// Búsqueda, filtro por categoría y paginación (RF-01 a RF-04). El estado vive
// en la URL (?categoria=&busqueda=&pagina=) para poder compartir y volver atrás.
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SearchX, ServerCrash } from "lucide-react";

import { catalogoApi } from "../api/endpoints";
import { usePrincipal } from "../features/catalogo/usePrincipal";
import Buscador from "../features/catalogo/Buscador";
import PildorasCategoria from "../features/catalogo/PildorasCategoria";
import GrillaProductos from "../features/catalogo/GrillaProductos";
import Paginacion from "../features/catalogo/Paginacion";
import EstadoVacio from "../components/ui/EstadoVacio";
import Boton from "../components/ui/Boton";
import { plural } from "../utils/format";
import s from "./CatalogoPage.module.css";

const POR_PAGINA = 12;

function enteroPositivo(valor) {
  const n = Number(valor);
  return Number.isInteger(n) && n >= 1 ? n : null;
}

export default function CatalogoPage() {
  const [params, setParams] = useSearchParams();
  const categoria = enteroPositivo(params.get("categoria"));
  const busqueda = (params.get("busqueda") ?? "").slice(0, 100);
  const pagina = enteroPositivo(params.get("pagina")) ?? 1;

  const [texto, setTexto] = useState(busqueda);
  const { data: principal } = usePrincipal();
  const categorias = principal?.categorias ?? [];

  // Si la URL cambia (atrás/adelante), sincronizar la caja de búsqueda.
  useEffect(() => setTexto(busqueda), [busqueda]);

  const actualizar = (cambios) => {
    const siguiente = new URLSearchParams(params);
    for (const [clave, valor] of Object.entries(cambios)) {
      if (valor === null || valor === "" || valor === undefined) siguiente.delete(clave);
      else siguiente.set(clave, String(valor));
    }
    setParams(siguiente, { replace: "pagina" in cambios ? false : true });
  };

  // Búsqueda en vivo con espera de 350 ms mientras se escribe.
  useEffect(() => {
    const limpio = texto.trim();
    if (limpio === busqueda.trim()) return;
    const t = window.setTimeout(() => actualizar({ busqueda: limpio, pagina: null }), 350);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [texto]);

  const consulta = useQuery({
    queryKey: ["productos", { categoria, busqueda: busqueda.trim(), pagina }],
    queryFn: ({ signal }) => catalogoApi.productos({ categoria, busqueda: busqueda.trim(), pagina, por_pagina: POR_PAGINA }, signal),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });
  const { data, isPending, isError, error, refetch, isPlaceholderData, isFetching } = consulta;

  const cambiarPagina = (n) => {
    actualizar({ pagina: n > 1 ? n : null });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const nombreCategoria = categorias.find((c) => c.id_categoria === categoria)?.nombre;
  const hayFiltros = Boolean(categoria || busqueda.trim());

  return (
    <div className={`contenedor ${s.pagina}`}>
      <header className={s.cabecera}>
        <h1 className={s.titulo}>{nombreCategoria ?? "Catálogo"}</h1>
        <p className={s.resumen} aria-live="polite">
          {data
            ? busqueda.trim()
              ? `${plural(data.total_resultados, "resultado")} para «${busqueda.trim()}»`
              : plural(data.total_resultados, "producto")
            : " "}
        </p>
      </header>

      <div className={s.filtros}>
        <div className={s.buscador}>
          <Buscador valor={texto} alCambiar={setTexto} />
        </div>
        {categorias.length > 0 && (
          <PildorasCategoria categorias={categorias} activa={categoria} alElegir={(id) => actualizar({ categoria: id, pagina: null })} />
        )}
      </div>

      <div className={s.barraCarga} data-activa={isFetching && !isPending ? "si" : "no"} aria-hidden />

      {isError ? (
        error.codigo === "parametro_invalido" ? (
          <EstadoVacio icono={SearchX} titulo="Esa búsqueda no es válida" accion={<Boton onClick={() => setParams({})}>Ver todo el catálogo</Boton>}>
            {error.message}
          </EstadoVacio>
        ) : (
          <EstadoVacio icono={ServerCrash} tono="error" titulo="No pudimos cargar los productos" accion={<Boton onClick={() => refetch()}>Reintentar</Boton>}>
            {error.message}
          </EstadoVacio>
        )
      ) : data && data.productos.length === 0 ? (
        <EstadoVacio
          icono={SearchX}
          titulo={pagina > 1 && data.total_resultados > 0 ? "Esta página no tiene productos" : "No se encontraron productos"}
          accion={
            hayFiltros ? (
              <Boton variante="secundario" onClick={() => setParams({})}>
                Quitar filtros
              </Boton>
            ) : null
          }
        >
          {hayFiltros ? "Prueba con otra palabra, revisa la referencia o elige otra categoría." : "Aún no hay productos publicados."}
        </EstadoVacio>
      ) : (
        <GrillaProductos productos={data?.productos ?? []} cargando={isPending} atenuada={isPlaceholderData} />
      )}

      {data && <Paginacion pagina={pagina} totalPaginas={data.total_paginas} alCambiar={cambiarPagina} />}
    </div>
  );
}
