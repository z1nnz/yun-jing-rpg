// Painted foliage clusters on cards (tools/art/build_species_trees_v1.py, z1nnz's leaf-cluster sheets): alpha-cut,
// both faces, lit with the crown's soft outward normals (from the model) so the whole crown shades as one mass,
// swaying more toward the top. A card turned edge-on to the camera fades out instead of showing as a streak: its
// face normal is taken from the screen-space derivatives of its position.
Shader "YunJing/QingxiFoliageCard"
{
    Properties
    {
        _BaseMap ("Foliage clusters", 2D) = "white" {}
        _BaseColor ("Tint", Color) = (1, 1, 1, 1)
        _Cutoff ("Alpha cut", Range(0, 1)) = .5
        _Height ("Tree height (m)", Float) = 10
        _Strength ("Wind (m at the top)", Float) = .08
    }
    SubShader
    {
        Tags { "RenderType" = "TransparentCutout" "Queue" = "AlphaTest" "RenderPipeline" = "UniversalPipeline" }
        Cull Off

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        CBUFFER_START(UnityPerMaterial)
            float4 _BaseMap_ST;
            half4 _BaseColor;
            half _Cutoff;
            float _Height, _Strength;
        CBUFFER_END
        TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);

        float3 Sway(float3 os, float3 ws)
        {
            float k = saturate(os.y / max(_Height, .1));
            float t = _Time.y;
            ws.xz += float2(sin(t * 1.1 + ws.x * .2 + ws.z * .13), cos(t * .9 + ws.z * .17)) * _Strength * k * k;
            return ws;
        }
        ENDHLSL

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
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct A { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct V { float4 positionCS : SV_POSITION; float3 ws : TEXCOORD0; float3 n : TEXCOORD1; float2 uv : TEXCOORD2; float fog : TEXCOORD3; };

            V Vert(A i)
            {
                UNITY_SETUP_INSTANCE_ID(i);
                V o;
                float3 ws = Sway(i.positionOS.xyz, TransformObjectToWorld(i.positionOS.xyz));
                o.ws = ws;
                o.positionCS = TransformWorldToHClip(ws);
                o.n = TransformObjectToWorldNormal(i.normalOS);
                o.uv = TRANSFORM_TEX(i.uv, _BaseMap);
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }

            half4 Frag(V i) : SV_Target
            {
                half4 c = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv) * _BaseColor;
                float3 view = GetWorldSpaceNormalizeViewDir(i.ws);
                float3 face = normalize(cross(ddy(i.ws), ddx(i.ws)));
                float facing = abs(dot(face, view));
                clip(c.a * smoothstep(.12, .38, facing) - _Cutoff);
                Light light = GetMainLight(TransformWorldToShadowCoord(i.ws));
                float3 n = normalize(i.n);
                float wrap = saturate(dot(n, light.direction) * .5 + .5);
                half3 ambient = SampleSH(n);
                half3 lit = c.rgb * (light.color * wrap * lerp(.5, 1, light.shadowAttenuation) + ambient * .9);
                return half4(MixFog(lit, i.fog), 1);
            }
            ENDHLSL
        }

        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }
            ColorMask 0
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing
            struct A { float4 positionOS : POSITION; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct V { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; };
            V Vert(A i)
            {
                UNITY_SETUP_INSTANCE_ID(i);
                V o;
                o.positionCS = TransformWorldToHClip(Sway(i.positionOS.xyz, TransformObjectToWorld(i.positionOS.xyz)));
                o.uv = TRANSFORM_TEX(i.uv, _BaseMap);
                return o;
            }
            half4 Frag(V i) : SV_Target
            {
                clip(SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv).a - _Cutoff);
                return 0;
            }
            ENDHLSL
        }
    }
}
