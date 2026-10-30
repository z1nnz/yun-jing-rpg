using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace YunJing.Editor
{
    // Trees built on z1nnz's Elder World Tree (elder-tree-esg; tools/art/build_elder_trees_v1.py,
    // art/exports/elder-trees-v1): the Guardian (建木, the hero itself, hanging roots and all) and its young one, and
    // seven species grown branch by branch at its level of finish (tools/art/build_species_trees_v1.py): camphor,
    // maple, ginkgo, willow, plum, pine, cypress and the withered tree, each with its own trunk, bark and leaf. Each FBX carries <Tree>_LOD0..2, so Unity builds the LOD group on import.
    // The leaves are coloured from a 64-swatch palette (one per tree): it must stay unfiltered and uncompressed.
    // FBX and textures are copied into a gitignored model folder, as the other collaborator kits are.
    public static class QingxiElderTrees
    {
        public const string Models = "Assets/YunJing/Models/ElderTreesV1";   // copied from art/exports, gitignored
        const string MaterialFolder = "Assets/QingxiWorld/Generated/Materials/ElderTrees";
        public static readonly string[] Kinds = { "ElderGuardian", "JianmuSapling", "ElderCamphor", "ElderMaple", "ElderGinkgo", "ElderWillow", "ElderPlum", "ElderPine", "ElderCypress", "ElderWithered" };

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
                var foliagePath = $"{Models}/{kind}_Foliage.png";
                var fi = (TextureImporter)AssetImporter.GetAtPath(foliagePath);
                if (fi != null && (!fi.alphaIsTransparency || fi.maxTextureSize != 1024))
                {
                    fi.alphaIsTransparency = true; fi.mipMapsPreserveCoverage = true; fi.alphaTestReferenceValue = .5f; fi.maxTextureSize = 1024; fi.SaveAndReimport();
                }
                var path = $"{Models}/{kind}_Leaves.png";
                var ti = (TextureImporter)AssetImporter.GetAtPath(path);
                if (ti == null) continue;   // painted foliage only
                if (ti.filterMode != FilterMode.Point || ti.mipmapEnabled || ti.textureCompression != TextureImporterCompression.Uncompressed)
                {
                    ti.filterMode = FilterMode.Point; ti.mipmapEnabled = false; ti.textureCompression = TextureImporterCompression.Uncompressed;
                    ti.wrapMode = TextureWrapMode.Clamp; ti.SaveAndReimport();
                }
            }
            foreach (var kind in Kinds)
            {
                // The Guardian and its sapling keep the source bark; each grown species has its own.
                string barkName = File.Exists(Path.Combine(dst, kind + "_Bark.png")) ? kind + "_Bark" : "ElderBark";
                var bark = Mat(barkName);
                bark.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>($"{Models}/{barkName}.png"));
                bark.SetColor("_BaseColor", Color.white); bark.SetFloat("_Smoothness", .12f);
                EditorUtility.SetDirty(bark);
                var path = $"{Models}/{kind}.fbx";
                var importer = (ModelImporter)AssetImporter.GetAtPath(path);
                if (importer == null) throw new FileNotFoundException("Elder tree missing", path);
                var leaves = Mat(kind + "_Leaves");
                // Painted foliage clusters (Elder<Species>_Foliage.png, alpha-cut) where the species has them;
                // otherwise the palette the leaf cards point into.
                var foliage = AssetDatabase.LoadAssetAtPath<Texture2D>($"{Models}/{kind}_Foliage.png");
                leaves.SetTexture("_BaseMap", foliage != null ? foliage : AssetDatabase.LoadAssetAtPath<Texture2D>($"{Models}/{kind}_Leaves.png"));
                leaves.SetFloat("_AlphaClip", foliage != null ? 1 : 0); leaves.SetFloat("_Cutoff", .5f);
                if (foliage != null) leaves.EnableKeyword("_ALPHATEST_ON"); else leaves.DisableKeyword("_ALPHATEST_ON");
                var card = Shader.Find("YunJing/QingxiFoliageCard");
                if (foliage != null && card != null) { leaves.shader = card; leaves.SetTexture("_BaseMap", foliage); leaves.SetFloat("_Cutoff", .5f); leaves.SetFloat("_Height", 12); }
                else leaves.shader = Shader.Find("Universal Render Pipeline/Lit");
                leaves.SetColor("_BaseColor", Color.white); leaves.SetFloat("_Smoothness", .08f);
                leaves.SetFloat("_Cull", 0);   // single-sided leaf cards
                EditorUtility.SetDirty(leaves);
                importer.bakeAxisConversion = true; importer.importAnimation = false; importer.importCameras = false; importer.importLights = false;
                importer.importNormals = ModelImporterNormals.Import;   // the source's volume normals shade the canopy softly
                importer.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
                importer.materialLocation = ModelImporterMaterialLocation.InPrefab;
                importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), barkName), bark);
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
