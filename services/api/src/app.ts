import 'reflect-metadata';
import { ArgumentsHost, Body, Catch, Controller, ExceptionFilter, Get, Headers, HttpException, Injectable, Module, Post } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { NestExpressApplication } from '@nestjs/platform-express';
import { resolve } from 'node:path';
import { randomBytes, timingSafeEqual } from 'node:crypto';
import { Database } from './database';
import { Game, GameError, content, estateContent, huntingContent, ensure, hash } from './game';
import { Auth } from './auth';
import { Action, HuntDeath } from '../../../packages/contracts/types';
import { chapter } from './journal';

export interface Configuration { mode: 'local' | 'production'; host: string; port: number; directory?: string; url?: string; internalKey?: string; speed: number }
export function configuration(env: NodeJS.ProcessEnv = process.env): Configuration {
  const mode = env.YUNJING_MODE ?? 'local';
  ensure(mode === 'local' || mode === 'production', 'CONFIG', '未知執行模式');
  const host = env.HOST ?? '127.0.0.1';
  if (mode === 'local') ensure(['127.0.0.1', '::1', 'localhost'].includes(host), 'CONFIG', '本機登入只能綁定 loopback');
  if (mode === 'production') {
    ensure(env.DATABASE_URL && env.FIREBASE_PROJECT_ID && (env.YUNJING_INTERNAL_KEY?.length ?? 0) >= 32, 'CONFIG', '正式環境需要獨立資料庫、Firebase 與內部憑證');
    ensure(!env.YUNJING_SPEED || env.YUNJING_SPEED === '1', 'CONFIG', '正式環境禁止加速');
  }
  const speed = mode === 'local' ? Number(env.YUNJING_SPEED ?? '60') : 1;
  const port = Number(env.PORT ?? '4310');
  ensure(Number.isFinite(speed) && speed >= 1 && speed <= 3600 && Number.isInteger(port) && port > 0 && port < 65536, 'CONFIG', '無效埠號或時間倍率');
  return { mode, host, port, speed, directory: env.YUNJING_DATA_DIR ?? '.data/postgres', url: env.DATABASE_URL, internalKey: env.YUNJING_INTERNAL_KEY };
}
@Catch()
export class ErrorFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    const response = host.switchToHttp().getResponse();
    if (exception instanceof GameError) return response.status(exception.status).json({ code: exception.code, message: exception.message });
    if (exception instanceof HttpException) return response.status(exception.getStatus()).json({ code: 'HTTP_ERROR', message: exception.message });
    console.error(exception instanceof Error ? exception.message : 'Internal failure');
    return response.status(500).json({ code: 'INTERNAL', message: '服務暫時無法完成操作，請使用相同請求編號重試' });
  }
}
@Injectable()
export class Runtime {
  config!: Configuration; game!: Game; auth!: Auth;
  internal(key?: string) {
    const expected = this.config.internalKey;
    ensure(expected && key && key.length < 500 && timingSafeEqual(Buffer.from(hash(key)), Buffer.from(hash(expected))), 'FORBIDDEN', '需要內部服務憑證', 403);
  }
}
@Controller('v1')
export class Api {
  constructor(private readonly runtime: Runtime) {}
  @Get('health') health() { return { status: 'ok', mode: this.runtime.config.mode, contentVersion: content.version, speed: this.runtime.game.speed }; }
  @Get('content') definitions() { return { ...content, chapter, estate: estateContent, hunting: huntingContent }; }
  @Get('auth/config') authConfig() {
    return process.env.FIREBASE_WEB_CONFIG ? JSON.parse(process.env.FIREBASE_WEB_CONFIG) : { unavailable: true };
  }
  @Post('auth/local') local(@Body() body: { alias?: unknown }) { return this.runtime.auth.local(body?.alias); }
  @Post('auth/challenge') challenge(@Body() body: { codeChallenge?: unknown }) { return this.runtime.auth.challenge(body?.codeChallenge); }
  @Post('auth/authorize') authorize(@Body() body: { challengeId?: unknown; firebaseToken?: unknown }) { return this.runtime.auth.authorize(body?.challengeId, body?.firebaseToken); }
  @Post('auth/exchange') exchange(@Body() body: { id?: unknown; verifier?: unknown }) { return this.runtime.auth.exchange(body?.id, body?.verifier); }
  @Post('auth/refresh') refresh(@Body() body: { refreshToken?: unknown }) { return this.runtime.auth.refresh(body?.refreshToken); }
  @Get('me') async me(@Headers('authorization') authorization?: string) {
    return this.runtime.game.snapshot(await this.runtime.auth.authenticate(authorization));
  }
  @Post('actions') async action(@Headers('authorization') authorization: string, @Body() body: { requestId: string; action: Action }) {
    ensure(body && typeof body.requestId === 'string' && body.action && typeof body.action === 'object' && !Array.isArray(body.action), 'INVALID_BODY', '操作格式不正確');
    return this.runtime.game.act(await this.runtime.auth.authenticate(authorization), body.requestId, body.action);
  }
  @Post('room/ticket') async ticket(@Headers('authorization') authorization: string) {
    const playerId = await this.runtime.auth.authenticate(authorization);
    const ticket = randomBytes(32).toString('base64url');
    await this.runtime.game.db.transaction(tx => tx.query('INSERT INTO room_tickets(ticket_hash,player_id,room_id,expires_at) VALUES($1,$2,$3,$4)', [hash(ticket), playerId, 'qingxi', this.runtime.game.now() + 60_000]));
    return { ticket, roomId: 'qingxi', host: '127.0.0.1', port: 7770, expiresIn: 60 };
  }
  @Post('internal/room/redeem') async redeem(@Headers('x-service-key') key: string, @Body() body: { ticket: string; roomId: string }) {
    this.runtime.internal(key); ensure(typeof body.ticket === 'string' && body.roomId === 'qingxi', 'INVALID_TICKET', '區域票證無效', 401);
    return this.runtime.game.db.transaction(async tx => {
      const row = (await tx.query<{ player_id: string; expires_at: string; consumed: boolean; room_id: string }>('SELECT * FROM room_tickets WHERE ticket_hash=$1 FOR UPDATE', [hash(body.ticket)])).rows[0];
      ensure(row && !row.consumed && row.room_id === body.roomId && Number(row.expires_at) > this.runtime.game.now(), 'INVALID_TICKET', '區域票證已失效', 401);
      await tx.query('UPDATE room_tickets SET consumed=true WHERE ticket_hash=$1', [hash(body.ticket)]);
      return { playerId: row.player_id };
    });
  }
  @Post('internal/transfers') transfer(@Headers('x-service-key') key: string, @Body() body: { id: string; playerId: string; linkId: string; quantity: number; cancel?: boolean }) {
    this.runtime.internal(key);
    return this.runtime.game.receiveTransfer(body);
  }
  @Post('internal/hunt/death') huntDeath(@Headers('x-service-key') key: string, @Body() body: HuntDeath) {
    this.runtime.internal(key);
    return this.runtime.game.settleHuntDeath(body);
  }
  @Post('internal/merchant/proximity') merchantProximity(@Headers('x-service-key') key: string, @Body() body: { playerId: string; roomId: string; merchantId: string }) {
    this.runtime.internal(key);
    return this.runtime.game.markMerchantProximity(body?.playerId, body?.roomId, body?.merchantId);
  }
}
@Module({ controllers: [Api], providers: [Runtime] })
class AppModule {}
export async function createApp(config: Configuration, database?: Database) {
  const game = new Game(database ?? new Database({ url: config.url, directory: config.directory }), { speed: config.speed });
  await game.initialize();
  const app = await NestFactory.create<NestExpressApplication>(AppModule, { logger: ['error', 'warn'] });
  const runtime = app.get(Runtime); runtime.config = config; runtime.game = game; runtime.auth = new Auth(game, config.mode);
  app.useGlobalFilters(new ErrorFilter());
  app.use((request: any, response: any, next: () => void) => {
    response.setHeader('X-Content-Type-Options', 'nosniff');
    response.setHeader('Referrer-Policy', 'no-referrer');
    if (request.path.startsWith('/v1')) response.setHeader('Cache-Control', 'no-store');
    next();
  });
  app.useStaticAssets(resolve('apps/inspector'));
  app.useStaticAssets(resolve('art/previews'), { prefix: '/art-previews/' });
  app.useStaticAssets(resolve('art/references'), { prefix: '/art-references/' });
  await app.init();
  return { app, game, auth: runtime.auth };
}
