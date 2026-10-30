// Stylized meadow grass and flowers for the terrain details (art/exports/qingxi-ground-v1): colour comes from the
// mesh's vertex colours (dark at the root, bright at the tip), blades sway more toward the tip, are lit mostly from
// above so a blade never flips dark when it faces away, and glow at the tip when the sun is behind them.
// Instanced (terrain details), both faces, receives the main light's shadows, takes the scene fog.
Shader "YunJing/QingxiGrass"
{
    Properties
    {
        _Tint ("Tint", Color) = (1, 1, 1, 1)
        _Wind ("Wind (m at the tip)", Float) = .1
        _Height ("Clump height (m)", Float) = .3
        _Ground ("Ground colour at the root", Color) = (.34, .5, .24, 1)
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry" "RenderPipeline" = "UniversalPipeline" }
        Cull Off
        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _Tint;
                half4 _Ground;
                float _Wind;
                float _Height;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                half4 color : COLOR;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                half4 color : COLOR;
                float tip : TEXCOORD2;
                float fog : TEXCOORD3;
            };

            Varyings Vert(Attributes input)
            {
                UNITY_SETUP_INSTANCE_ID(input);
                Varyings o;
                float3 ws = TransformObjectToWorld(input.positionOS.xyz);
                float tip = saturate(input.positionOS.y / max(_Height, .01));
                float t = _Time.y;
                float gust = sin(t * .7 + ws.x * .05) * .5 + .5;
                float2 sway = float2(sin(t * 1.8 + ws.x * .35 + ws.z * .2), cos(t * 1.4 + ws.z * .31 + ws.x * .1)) * _Wind * (.6 + gust) * tip * tip;
                ws.xz += sway;
                o.positionWS = ws;
                o.positionCS = TransformWorldToHClip(ws);
                o.normalWS = TransformObjectToWorldNormal(input.normalOS);
                o.color = input.color;
                o.tip = tip;
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }

            half4 Frag(Varyings i, bool front : SV_IsFrontFace) : SV_Target
            {
                Light light = GetMainLight(TransformWorldToShadowCoord(i.positionWS));
                float3 n = normalize(lerp(normalize(i.normalWS) * (front ? 1 : -1), float3(0, 1, 0), .65));
                float diffuse = saturate(dot(n, light.direction)) * .6 + .4;
                // The root takes the colour of the turf it grows from and the blade only finds its own colour toward
                // the tip, so the grass grows out of the ground instead of standing on it.
                half3 albedo = lerp(_Ground.rgb, i.color.rgb * _Tint.rgb, smoothstep(.0, .55, i.tip));
                half3 ambient = SampleSH(float3(0, 1, 0));
                half3 c = albedo * (light.color * diffuse * lerp(.45, 1, light.shadowAttenuation) + ambient);
                float3 view = GetWorldSpaceNormalizeViewDir(i.positionWS);
                c += albedo * light.color * pow(saturate(dot(-view, light.direction)), 4) * i.tip * .4;   // backlit tips
                return half4(MixFog(c, i.fog), 1);
            }
            ENDHLSL
        }
    }
}
