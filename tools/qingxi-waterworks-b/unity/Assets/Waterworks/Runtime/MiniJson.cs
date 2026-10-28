// Small JSON reader/writer for the site tables, scenarios and golden files (JsonUtility cannot do dictionaries).
// Objects become Dictionary<string, object> (insertion order kept), arrays List<object>, numbers double.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace Qingxi.Waterworks
{
    public static class MiniJson
    {
        public static object Parse(string s) { int i = 0; var v = Value(s, ref i); Ws(s, ref i); if (i != s.Length) throw new FormatException($"trailing data at {i}"); return v; }

        static void Ws(string s, ref int i) { while (i < s.Length && char.IsWhiteSpace(s[i])) i++; }

        static object Value(string s, ref int i)
        {
            Ws(s, ref i);
            if (i >= s.Length) throw new FormatException("unexpected end");
            char c = s[i];
            if (c == '{')
            {
                var d = new Dictionary<string, object>(); i++; Ws(s, ref i);
                if (s[i] == '}') { i++; return d; }
                while (true)
                {
                    Ws(s, ref i); var k = Str(s, ref i); Ws(s, ref i);
                    if (s[i++] != ':') throw new FormatException($"':' expected at {i}");
                    d[k] = Value(s, ref i); Ws(s, ref i);
                    if (s[i] == ',') { i++; continue; }
                    if (s[i] == '}') { i++; return d; }
                    throw new FormatException($"',' or '}}' expected at {i}");
                }
            }
            if (c == '[')
            {
                var l = new List<object>(); i++; Ws(s, ref i);
                if (s[i] == ']') { i++; return l; }
                while (true)
                {
                    l.Add(Value(s, ref i)); Ws(s, ref i);
                    if (s[i] == ',') { i++; continue; }
                    if (s[i] == ']') { i++; return l; }
                    throw new FormatException($"',' or ']' expected at {i}");
                }
            }
            if (c == '"') return Str(s, ref i);
            if (s.Length - i >= 4 && string.CompareOrdinal(s, i, "true", 0, 4) == 0) { i += 4; return true; }
            if (s.Length - i >= 5 && string.CompareOrdinal(s, i, "false", 0, 5) == 0) { i += 5; return false; }
            if (s.Length - i >= 4 && string.CompareOrdinal(s, i, "null", 0, 4) == 0) { i += 4; return null; }
            int st = i;
            while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0) i++;
            return double.Parse(s.Substring(st, i - st), CultureInfo.InvariantCulture);
        }

        static string Str(string s, ref int i)
        {
            if (s[i] != '"') throw new FormatException($"string expected at {i}");
            var b = new StringBuilder(); i++;
            while (s[i] != '"')
            {
                char c = s[i++];
                if (c != '\\') { b.Append(c); continue; }
                char e = s[i++];
                switch (e)
                {
                    case 'n': b.Append('\n'); break;
                    case 't': b.Append('\t'); break;
                    case 'r': b.Append('\r'); break;
                    case 'b': b.Append('\b'); break;
                    case 'f': b.Append('\f'); break;
                    case 'u': b.Append((char)Convert.ToInt32(s.Substring(i, 4), 16)); i += 4; break;
                    default: b.Append(e); break;
                }
            }
            i++; return b.ToString();
        }

        public static string Write(object v)
        {
            var b = new StringBuilder(); W(b, v); return b.ToString();
        }

        static void W(StringBuilder b, object v)
        {
            switch (v)
            {
                case null: b.Append("null"); break;
                case string s:
                    b.Append('"');
                    foreach (var c in s)
                    {
                        if (c == '"' || c == '\\') b.Append('\\').Append(c);
                        else if (c == '\n') b.Append("\\n");
                        else if (c < ' ') b.Append("\\u").Append(((int)c).ToString("x4"));
                        else b.Append(c);
                    }
                    b.Append('"'); break;
                case bool x: b.Append(x ? "true" : "false"); break;
                case double d: b.Append(d.ToString("R", CultureInfo.InvariantCulture)); break;
                case int n: b.Append(n.ToString(CultureInfo.InvariantCulture)); break;
                case IDictionary d:
                    b.Append('{'); bool first = true;
                    foreach (DictionaryEntry e in d) { if (!first) b.Append(','); first = false; W(b, e.Key.ToString()); b.Append(':'); W(b, e.Value); }
                    b.Append('}'); break;
                case IEnumerable l:
                    b.Append('['); bool f2 = true;
                    foreach (var e in l) { if (!f2) b.Append(','); f2 = false; W(b, e); }
                    b.Append(']'); break;
                default: b.Append(Convert.ToString(v, CultureInfo.InvariantCulture)); break;
            }
        }

        // ---- typed access helpers
        public static Dictionary<string, object> O(object v) => (Dictionary<string, object>)v;
        public static List<object> L(object v) => (List<object>)v;
        public static int I(object v) => (int)Convert.ToDouble(v, CultureInfo.InvariantCulture);
        public static double D(object v) => Convert.ToDouble(v, CultureInfo.InvariantCulture);
        public static string S(object v) => (string)v;
    }
}
