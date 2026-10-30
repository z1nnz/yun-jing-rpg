using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace YunJing.Editor
{
    // Trees built on z1nnz's Elder World Tree (elder-tree-esg; tools/art/build_elder_trees_v1.py,
    // art/exports/elder-trees-v1): the Guardian (the hero itself, hanging roots and all) and seven species reshaped
    // from it: camphor, maple, ginkgo, willow, plum, cypress and a sapling (each its own trunk curve, girth and crown). Each FBX carries <Tree>_LOD0..2, so Unity builds the LOD group on import.
    // The leaves are coloured from a 64-swatch palette (one per tree): it must stay unfiltered and uncompressed.
    // FBX and textures are copied into a gitignored model folder, as the other collaborator kits are.
    public static class QingxiElderTrees
    {
        public const string Models = "Assets/YunJing/Models/ElderTreesV1";   // copied from art/exports, gitignored
        const string MaterialFolder = "Assets/QingxiWorld/Generated/Materials/ElderTrees";
        public static readonly string[] Kinds = { "ElderGuardian", "ElderCamphor", "ElderMaple", "ElderGinkgo", "ElderWillow", "ElderPlum", "ElderCypress", "ElderSapling" };

        public static GameObject Source(string kind) => AssetDatabase.LoadAssetAtPath<GameObject>($"{Models}/{kind}.fbx");

        /// <summary>True when the tree kit is in this checkout (art/exports/elder-trees-v1 pulled from LFS).</summary>
        public static bool Available => File.Exists(Path.Combine(Repo, "art/exports/elder-trees-v1/ElderCamphor.fbx"));

        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", ".."));

        public static void Copy()
        {
            string src = Path.Combine(Repo, "art/exports/elder-trees-v1"), dst = Path.Combine(Repo, "apps/game", Models);
            Directory.CreateDirectory(dst);
            foreach (var pattern in new[] { "*.fbx", "*.png" })
                foreach (var file in Directory.GetFiles(src, pattern))
                {
                    if (new FileInfo(file).Length < 200) throw new InvalidOperationException("Git LFS pointer instead of asset; run git lfs pull: " + file);
                    var target = Path.Combine(dst, Path.GetFileName(file));
                    if (!File.Exists(target) || new FileInfo(target).Length != new FileInfo(file).Length) File.Copy(file, target, true);
                }
            AssetDatabase.Refresh();
            Directory.CreateDirectory(Path.Combine(Repo, "apps/game", MaterialFolder));
            foreach (var kind in Kinds)
            {
                var path = $"{Models}/{kind}_Leaves.png";
                var ti = (TextureImporter)AssetImporter.GetAtPath(path);
                if (ti == null) throw new FileNotFoundException("Elder tree palette missing", path);
                if (ti.filterMode != FilterMode.Point || ti.mipmapEnabled || ti.textureCompression != TextureImporterCompression.Uncompressed)
                {
                    ti.filterMode = FilterMode.Point; ti.mipmapEnabled = false; ti.textureCompression = TextureImporterCompression.Uncompressed;
                    ti.wrapMode = TextureWrapMode.Clamp; ti.SaveAndReimport();
                }
            }
            var bark = Mat("ElderBark");
            bark.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>($"{Models}/ElderBark.png"));
            bark.SetColor("_BaseColor", Color.white); bark.SetFloat("_Smoothness", .12f);
            EditorUtility.SetDirty(bark);
            foreach (var kind in Kinds)
            {
                var path = $"{Models}/{kind}.fbx";
                var importer = (ModelImporter)AssetImporter.GetAtPath(path);
                if (importer == null) throw new FileNotFoundException("Elder tree missing", path);
                var leaves = Mat(kind + "_Leaves");
                leaves.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>($"{Models}/{kind}_Leaves.png"));
                leaves.SetColor("_BaseColor", Color.white); leaves.SetFloat("_Smoothness", .08f);
                leaves.SetFloat("_Cull", 0);   // single-sided leaf cards
                EditorUtility.SetDirty(leaves);
                importer.bakeAxisConversion = true; importer.importAnimation = false; importer.importCameras = false; importer.importLights = false;
                importer.importNormals = ModelImporterNormals.Import;   // the source's volume normals shade the canopy softly
                importer.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
                importer.materialLocation = ModelImporterMaterialLocation.InPrefab;
                importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "ElderBark"), bark);
                importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), kind + "_Leaves"), leaves);
                importer.SaveAndReimport();
            }
        }

        static Material Mat(string name)
        {
            var path = $"{MaterialFolder}/{name}_URP.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) { mat = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(mat, path); }
            return mat;
        }
    }
}
