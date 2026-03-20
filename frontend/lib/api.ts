const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Deputado {
  id: string;
  nome: string;
  siglaPartido: string;
  siglaUf: string;
  idLegislatura: string;
  urlFoto: string;
  email: string;
}

export interface DetalhesDeputado {
  id: number;
  nomeCivil: string;
  cpf: string;
  sexo: string;
  dataNascimento: string;
  ufNasc: string;
  municipioNasc: string;
  escolaridade: string;
  urlRedeSocial?: string;
}

export interface DespesaTipo {
  tipoDespesa: string;
  somaValorLiquido: number;
  rankGastador: number;
  rankEconomizador: number;
  idLegislatura: string;
}

export interface DespesaMensal {
  idLegislatura: string;
  ano: string;
  mes: string;
  tipoDespesa: string;
  somaValorLiquido: number;
}

export interface ZScore {
  idDeputado: string;
  valorTotal: number;
  media: number;
  desvioPadrao: number;
  zScore: number;
  classificacao: "Normal" | "Atencao" | "Outlier";
  totalDeputadosAvaliados: number;
}

export interface RankingItem {
  idDeputado: string;
  nome: string;
  siglaPartido: string;
  siglaUf: string;
  urlFoto: string;
  valorTotal: number;
  rankGastador: number;
  idLegislatura: string;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`Erro ${res.status}: ${await res.text()}`);
  return res.json();
}

export const api = {
  buscarDeputados: (q: string) =>
    get<Deputado[]>(`/deputados?q=${encodeURIComponent(q)}`),

  listarDeputados: () => get<Deputado[]>(`/deputados`),

  perfilDeputado: (id: string) => get<Deputado>(`/deputados/${id}`),

  detalhesDeputado: (id: string) =>
    get<DetalhesDeputado>(`/deputados/${id}/detalhes`),

  despesasPorTipo: (id: string, legislatura?: string) => {
    const qs = legislatura ? `?idLegislatura=${legislatura}` : "";
    return get<DespesaTipo[]>(`/deputados/${id}/despesas${qs}`);
  },

  despesasMensais: (id: string, legislatura?: string) => {
    const qs = legislatura ? `?idLegislatura=${legislatura}` : "";
    return get<DespesaMensal[]>(`/deputados/${id}/despesas/mensal${qs}`);
  },

  zscoreDeputado: (id: string, legislatura?: string) => {
    const qs = legislatura ? `?idLegislatura=${legislatura}` : "";
    return get<ZScore>(`/deputados/${id}/despesas/zscore${qs}`);
  },

  ranking: (legislatura?: string, limite = 50) => {
    const qs = new URLSearchParams();
    if (legislatura) qs.set("idLegislatura", legislatura);
    qs.set("limite", String(limite));
    return get<RankingItem[]>(`/ranking?${qs}`);
  },

  legislaturas: () => get<string[]>(`/legislaturas`),
};
