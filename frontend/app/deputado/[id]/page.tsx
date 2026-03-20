"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  Legend,
} from "recharts";
import {
  ArrowLeft,
  Mail,
  Loader2,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Instagram,
  Twitter,
  Facebook,
  Youtube,
  Globe,
  User,
  Calendar,
  GraduationCap,
  MapPin,
} from "lucide-react";
import {
  api,
  Deputado,
  DespesaTipo,
  DespesaMensal,
  ZScore,
  DetalhesDeputado,
} from "@/lib/api";

const BRL = (v: number) =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(v);

const ZSCORE_COLOR: Record<string, string> = {
  Normal: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  Atencao: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  Outlier: "bg-red-500/20 text-red-400 border-red-500/30",
};

const ZSCORE_LABEL: Record<string, string> = {
  Normal: "Normal",
  Atencao: "Atenção",
  Outlier: "Outlier",
};

export default function PerfilDeputado() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [perfil, setPerfil] = useState<Deputado | null>(null);
  const [detalhes, setDetalhes] = useState<DetalhesDeputado | null>(null);
  const [despesas, setDespesas] = useState<DespesaTipo[]>([]);
  const [mensal, setMensal] = useState<DespesaMensal[]>([]);
  const [zscore, setZscore] = useState<ZScore | null>(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setErro(""); // Reset erro ao iniciar nova busca

    // Executamos as chamadas obrigatórias separadas das opcionais (Z-Score)
    // para que a falha no Z-Score não impeça de ver o perfil e despesas
    const fetchDadosObrigatorios = Promise.all([
      api.perfilDeputado(id),
      api.despesasPorTipo(id).catch(() => []), // Se falhar, retorna vazio mas segue
      api.despesasMensais(id).catch(() => []), // Se falhar, retorna vazio mas segue
    ]);

    const fetchZScore = api.zscoreDeputado(id).catch((e) => {
      console.warn("Falha ao carregar Z-Score individual:", e.message);
      return null; // Retorna null se não houver dados consolidados
    });

    const fetchDetalhes = api.detalhesDeputado(id).catch((e) => {
      console.warn("Falha ao carregar detalhes extras:", e.message);
      return null;
    });

    Promise.all([fetchDadosObrigatorios, fetchZScore, fetchDetalhes])
      .then(([[p, d, m], z, det]) => {
        setPerfil(p);
        setDespesas(d);
        setMensal(m);
        setZscore(z);
        setDetalhes(det);
      })
      .catch((e) => {
        console.error("Erro fatal no carregamento:", e);
        setErro(e.message);
      })
      .finally(() => setLoading(false));
  }, [id]);

  // Agrupa dados mensais em série temporal somando todos os tipos
  const seriesMensal = Object.values(
    mensal.reduce<Record<string, { periodo: string; total: number }>>(
      (acc, row) => {
        const key = `${row.ano}-${String(row.mes).padStart(2, "0")}`;
        acc[key] = {
          periodo: key,
          total: (acc[key]?.total ?? 0) + row.somaValorLiquido,
        };
        return acc;
      },
      {},
    ),
  ).sort((a, b) => a.periodo.localeCompare(b.periodo));

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-10 h-10 text-blue-400 animate-spin" />
      </div>
    );
  }

  if (erro || !perfil) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center gap-4 text-white">
        <AlertTriangle className="w-12 h-12 text-red-400" />
        <p className="text-lg">{erro || "Deputado não encontrado."}</p>
        <button
          onClick={() => router.back()}
          className="text-blue-400 hover:underline"
        >
          ← Voltar
        </button>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="max-w-5xl mx-auto px-4 py-10 space-y-8">
        {/* Voltar */}
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Voltar à busca
        </button>

        {/* Perfil Card */}
        <div className="flex flex-col sm:flex-row gap-6 bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <div className="relative w-28 h-28 rounded-2xl overflow-hidden flex-shrink-0 bg-slate-800 mx-auto sm:mx-0">
            {perfil.urlFoto ? (
              <Image
                src={perfil.urlFoto}
                alt={perfil.nome}
                fill
                className="object-cover"
                unoptimized
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-5xl font-bold text-slate-500">
                {perfil.nome.charAt(0)}
              </div>
            )}
          </div>
          <div className="flex-1 text-center sm:text-left">
            <h1 className="text-2xl font-bold mb-1">{perfil.nome}</h1>
            <p className="text-slate-400 text-lg mb-4">
              {perfil.siglaPartido} · {perfil.siglaUf} · Legislatura{" "}
              {perfil.idLegislatura}
            </p>

            <div className="flex flex-col gap-2 mb-4 text-sm text-slate-300">
              {perfil.email && (
                <a
                  href={`mailto:${perfil.email}`}
                  className="flex items-center gap-2 text-blue-400 hover:underline justify-center sm:justify-start"
                >
                  <Mail className="w-4 h-4" /> {perfil.email}
                </a>
              )}
              {detalhes && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
                  {detalhes.dataNascimento && (
                    <div className="flex items-center gap-2 justify-center sm:justify-start text-slate-400">
                      <Calendar className="w-4 h-4" />{" "}
                      {new Date(detalhes.dataNascimento).toLocaleDateString(
                        "pt-BR",
                      )}
                    </div>
                  )}
                  {detalhes.escolaridade && (
                    <div className="flex items-center gap-2 justify-center sm:justify-start text-slate-400">
                      <GraduationCap className="w-4 h-4" />{" "}
                      {detalhes.escolaridade}
                    </div>
                  )}
                  {detalhes.municipioNasc && (
                    <div className="flex items-center gap-2 justify-center sm:justify-start text-slate-400 col-span-1 sm:col-span-2">
                      <MapPin className="w-4 h-4" /> {detalhes.municipioNasc} /{" "}
                      {detalhes.ufNasc}
                    </div>
                  )}
                </div>
              )}
            </div>

            {detalhes?.urlRedeSocial && (
              <div className="flex flex-wrap gap-2 mt-4 justify-center sm:justify-start">
                {(detalhes.urlRedeSocial.includes("[")
                  ? JSON.parse(detalhes.urlRedeSocial.replace(/'/g, '"'))
                  : detalhes.urlRedeSocial.split(",")
                ).map((url: string, i: number) => {
                  const u = url.trim();
                  if (!u || u === "None" || u === "[]") return null;

                  let Icon = Globe;
                  if (u.toLowerCase().includes("instagram.com"))
                    Icon = Instagram;
                  else if (
                    u.toLowerCase().includes("twitter.com") ||
                    u.toLowerCase().includes("x.com")
                  )
                    Icon = Twitter;
                  else if (u.toLowerCase().includes("facebook.com"))
                    Icon = Facebook;
                  else if (u.toLowerCase().includes("youtube.com"))
                    Icon = Youtube;

                  return (
                    <a
                      key={i}
                      href={u.startsWith("http") ? u : `https://${u}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700"
                      title={u}
                    >
                      <Icon className="w-4 h-4" />
                    </a>
                  );
                })}
              </div>
            )}
          </div>

          {/* Z-Score Badge */}
          {zscore && (
            <div className="flex flex-col items-center justify-center gap-2 bg-slate-800 rounded-xl p-4 min-w-[160px]">
              <span className="text-xs text-slate-400 uppercase tracking-wide">
                Gastos vs. Média
              </span>
              <span
                className={`text-2xl font-bold px-3 py-1 rounded-full border ${ZSCORE_COLOR[zscore.classificacao]}`}
              >
                Z = {zscore.zScore.toFixed(2)}
              </span>
              <span
                className={`text-sm font-medium ${ZSCORE_COLOR[zscore.classificacao].split(" ")[1]}`}
              >
                {zscore.classificacao === "Atencao" ? (
                  <span className="flex items-center gap-1">
                    <TrendingUp className="w-3.5 h-3.5" />{" "}
                    {ZSCORE_LABEL[zscore.classificacao]}
                  </span>
                ) : zscore.classificacao === "Outlier" ? (
                  <span className="flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" /> Outlier
                  </span>
                ) : (
                  <span className="flex items-center gap-1">
                    <TrendingDown className="w-3.5 h-3.5" /> Normal
                  </span>
                )}
              </span>
              <span className="text-xs text-slate-500">
                Total: {BRL(zscore.valorTotal)}
              </span>
              <span className="text-xs text-slate-500">
                Média geral: {BRL(zscore.media)}
              </span>
            </div>
          )}
        </div>

        {/* Gastos por tipo */}
        {despesas.length > 0 && (
          <section className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-lg font-semibold mb-6">
              Gastos por Tipo de Despesa
            </h2>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={despesas}
                layout="vertical"
                margin={{ left: 10, right: 30 }}
              >
                <XAxis
                  type="number"
                  tickFormatter={(v) => BRL(v)}
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                />
                <YAxis
                  type="category"
                  dataKey="tipoDespesa"
                  width={200}
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                />
                <Tooltip
                  formatter={(v: number) => BRL(v)}
                  contentStyle={{
                    background: "#1e293b",
                    border: "1px solid #334155",
                    borderRadius: 8,
                  }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Bar
                  dataKey="somaValorLiquido"
                  fill="#3b82f6"
                  radius={[0, 4, 4, 0]}
                  name="Valor Líquido"
                />
              </BarChart>
            </ResponsiveContainer>
          </section>
        )}

        {/* Evolução Mensal */}
        {seriesMensal.length > 0 && (
          <section className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-lg font-semibold mb-6">
              Evolução Mensal dos Gastos
            </h2>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={seriesMensal} margin={{ left: 10, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="periodo"
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                />
                <YAxis
                  tickFormatter={(v) => BRL(v)}
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                  width={90}
                />
                <Tooltip
                  formatter={(v: number) => BRL(v)}
                  contentStyle={{
                    background: "#1e293b",
                    border: "1px solid #334155",
                    borderRadius: 8,
                  }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="total"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                  name="Total Mensal"
                />
              </LineChart>
            </ResponsiveContainer>
          </section>
        )}

        {despesas.length === 0 && seriesMensal.length === 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-10 text-center text-slate-500">
            Sem dados de despesas disponíveis para este deputado.
          </div>
        )}
      </div>
    </main>
  );
}
