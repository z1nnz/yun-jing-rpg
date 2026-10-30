// The novice world's sky: a clear blue that deepens overhead and pales into haze at the horizon, soft drifting
// cumulus, and a gentle sun. Same properties as Skybox/Procedural where QingxiDayNight drives them (_SkyTint,
// _GroundColor, _Exposure), so the clock still colours dawn, dusk and night.
Shader "YunJing/QingxiSky"
{
    Properties
    {
        _SkyTint ("Sky tint", Color) = (.5, .62, .74, 1)
        _GroundColor ("Horizon haze", Color) = (.78, .83, .84, 1)
        _Exposure ("Exposure", Float) = 1.2
        _SunSize ("Sun size", Float) = .035
        _Clouds ("Cloud cover", Range(0, 1)) = .5
    }
    SubShader
    {
        Tags { "Queue" = "Background" "RenderType" = "Background" "PreviewType" = "Skybox" "RenderPipeline" = "UniversalPipeline" }
        Cull Off ZWrite Off
        Pass
        {
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _SkyTint;
                half4 _GroundColor;
                float _Exposure;
                float _SunSize;
                float _Clouds;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 dir : TEXCOORD0; };

            Varyings Vert(Attributes input)
            {
                Varyings o;
                o.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                o.dir = input.positionOS.xyz;
                return o;
            }

            float Hash(float2 p) { return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453); }
            float Noise(float2 p)
            {
                float2 i = floor(p), f = frac(p);
                f = f * f * (3 - 2 * f);
                return lerp(lerp(Hash(i), Hash(i + float2(1, 0)), f.x), lerp(Hash(i + float2(0, 1)), Hash(i + 1), f.x), f.y);
            }
            float Fbm(float2 p)
            {
                float v = 0, a = .5;
                for (int k = 0; k < 5; k++) { v += a * Noise(p); p = p * 2.03 + 17.1; a *= .5; }
                return v;
            }

            half4 Frag(Varyings i) : SV_Target
            {
                float3 d = normalize(i.dir);
                float up = d.y;
                float3 sun = normalize(_MainLightPosition.xyz);
                half3 zenith = _SkyTint.rgb * half3(.62, .85, 1.25);
                half3 horizon = lerp(_GroundColor.rgb, half3(.86, .92, .97), .45);
                half3 c = lerp(horizon, zenith, pow(saturate(up), .5));
                c = lerp(c, _GroundColor.rgb * .85, saturate(-up * 5));   // below the horizon: haze
                // Cumulus on a dome: noise projected from the view direction, drifting slowly, thinning to the horizon.
                float2 uv = d.xz / (up + .18) * .55 + _Time.y * float2(.003, .0012);
                float n = Fbm(uv * 1.4);
                float cover = smoothstep(1 - _Clouds, 1.05 - _Clouds * .7, n) * smoothstep(.0, .22, up);
                float lit = saturate(Fbm(uv * 1.4 + sun.xz * .08) - n + .55);   // brighter on the sun side of each cloud
                half3 cloud = lerp(half3(.72, .77, .86) * _SkyTint.rgb * 1.6, half3(1, .99, .96), lit);
                c = lerp(c, cloud, cover * .92);
                // The sun: a small soft disc and a wide glow.
                float s = saturate(dot(d, sun));
                c += half3(1, .93, .8) * (pow(s, 900 / max(_SunSize * 30, .1)) * 3 + pow(s, 12) * .25) * (1 - cover * .8);
                return half4(c * _Exposure * .82, 1);
            }
            ENDHLSL
        }
    }
}
