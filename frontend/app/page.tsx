"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { Search, Loader2, Users } from "lucide-react";
import { api, Deputado } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Deputado[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const search = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([]);
      setSearched(false);
      return;
    }
    setLoading(true);
    try {
      const data = await api.buscarDeputados(q);
      setResults(data);
      setSearched(true);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const debouncedSearch = useCallback(
    (() => {
      let timer: ReturnType<typeof setTimeout>;
      return (v: string) => {
        clearTimeout(timer);
        timer = setTimeout(() => search(v), 400);
      };
    })(),
    [search],
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setQuery(v);
    debouncedSearch(v);
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-950 to-slate-900 text-white">
      <div className="max-w-3xl mx-auto px-4 py-20">
        <div className="text-center mb-12">
          <div className="flex justify-center mb-4">
            <Users className="w-12 h-12 text-blue-400" />
          </div>
          <h1 className="text-4xl font-bold tracking-tight mb-3">
            Transparência dos Deputados
          </h1>
          <p className="text-slate-400 text-lg">
            Pesquise qualquer deputado federal e veja seus gastos e perfil
            completo.
          </p>
        </div>

        <div className="relative mb-8">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            value={query}
            onChange={handleChange}
            placeholder="Digite o nome do deputado..."
            className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-12 pr-4 py-4 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 text-lg"
            autoFocus
          />
          {loading && (
            <Loader2 className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-blue-400 animate-spin" />
          )}
        </div>

        {searched && results.length === 0 && (
          <p className="text-center text-slate-400 mt-8">
            Nenhum deputado encontrado para &quot;{query}&quot;.
          </p>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {results.map((dep) => (
            <button
              key={dep.id}
              onClick={() => router.push(`/deputado/${dep.id}`)}
              className="flex items-center gap-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-blue-500 rounded-xl p-4 text-left transition-all group"
            >
              <div className="relative w-14 h-14 rounded-full overflow-hidden flex-shrink-0 bg-slate-700">
                {dep.urlFoto ? (
                  <Image
                    src={dep.urlFoto}
                    alt={dep.nome}
                    fill
                    className="object-cover"
                    unoptimized
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-slate-400 text-xl font-bold">
                    {dep.nome.charAt(0)}
                  </div>
                )}
              </div>
              <div className="overflow-hidden">
                <p className="font-semibold text-white group-hover:text-blue-400 truncate transition-colors">
                  {dep.nome}
                </p>
                <p className="text-sm text-slate-400">
                  {dep.siglaPartido} · {dep.siglaUf}
                </p>
              </div>
            </button>
          ))}
        </div>
      </div>
    </main>
  );
}
