// Every table a client needs to draw the site and re-run the rules. The Blender scene gets it through cli.mjs; the
// Unity port reads the same export from unity/Assets/Resources/waterworks-site.json (written by tests/make-golden.mjs).
import { STOCK, STOCK_ZH, OUTCOMES } from './waterworks-core.mjs';
import { FIXTURES, OBSERVATIONS, UNKNOWN } from './fixtures.mjs';
import { PIECES, DIRECTIONS, SOURCE, TARGETS, TERRAIN, LOSS, W, H, FIELD_DEMAND } from './site.mjs';

export const siteTables = () => ({ W, H, PIECES, DIRECTIONS, SOURCE, TARGETS, TERRAIN, LOSS, FIELD_DEMAND, FIXTURES, OBSERVATIONS, UNKNOWN, STOCK, STOCK_ZH, OUTCOMES });
