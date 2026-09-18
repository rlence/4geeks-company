"""Preparación e indexación del corpus de conocimiento (Hito 7).

Lee los documentos de docs/company-knowledge-base/, los parte en chunks
semánticos y los inserta en la colección Qdrant `brasaland_knowledge`.

El chunking es a medida de este corpus concreto, y la razón está medida:
los cuatro documentos tienen UN solo encabezado Markdown —el `#` del
título— y cero `##`/`###`. Chunkear por nivel de encabezado produciría un
chunk por documento, justo lo que el CONTEXT §5 prohíbe. La estructura
semántica real vive en bloques separados por línea en blanco, donde varios
son una línea de entrada terminada en `:` seguida de su lista.

data/pipelines/rag.py consume `embed()` de aquí para embeber la pregunta
del usuario: es la misma función al indexar y al consultar, como exige el
rule.

El módulo se llama rag_index y no rag —como sugiere la tabla del rule, que
admite otros nombres— porque dos módulos `rag.py` en el mismo sys.path
colisionan: `from rag import ...` desde data/pipelines/rag.py se resolvería
al propio archivo. El nombre describe además su responsabilidad real:
preparar el corpus e indexarlo.
"""

import hashlib
import os
import re
import uuid
from pathlib import Path

from qdrant_client import QdrantClient, models

KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parents[2] / "docs" / "company-knowledge-base"
COLLECTION_NAME = "brasaland_knowledge"
COMPANY = "brasaland"
LANGUAGE = "es"

# Nombre de archivo -> valor literal de `source_document` en el payload
# (CONTEXT §3). El briefing de empresa NO está aquí a propósito: no forma
# parte de la tabla de documentos fuente del CONTEXT §2.
SOURCE_DOCUMENTS = {
    "brasaland-loyalty-program.es.md": "loyalty-program",
    "brasaland-waste-protocol.es.md": "waste-protocol",
    "brasaland-menu-allergens.es.md": "menu-allergens",
    "brasaland-supplier-ordering.es.md": "supplier-ordering",
}

MIN_CHUNKS_PER_DOCUMENT = 3

# Namespace fijo para los IDs deterministas de los puntos. Cualquier UUID
# constante sirve; lo que importa es que no cambie entre corridas.
_ID_NAMESPACE = uuid.UUID("b8a5f3d2-1c4e-4a7b-9f60-2d8e1a3c5b70")

_openai_client = None
_qdrant_client = None


# --------------------------------------------------------------------------
# Lectura y chunking — funciones puras, sin red. Testeables tal cual.
# --------------------------------------------------------------------------


def load_documents() -> list[dict]:
    """Lee el corpus de docs/company-knowledge-base/ en orden estable."""
    if not KNOWLEDGE_BASE_DIR.is_dir():
        raise FileNotFoundError(
            f"No existe {KNOWLEDGE_BASE_DIR}. Copia los documentos fuente del "
            f"CONTEXT §2 antes de indexar."
        )

    documents = []
    for filename, source_document in sorted(SOURCE_DOCUMENTS.items()):
        path = KNOWLEDGE_BASE_DIR / filename
        if not path.is_file():
            raise FileNotFoundError(
                f"Falta el documento fuente {filename} en {KNOWLEDGE_BASE_DIR}."
            )
        documents.append(
            {"source_document": source_document, "text": path.read_text(encoding="utf-8")}
        )

    if not documents:
        raise ValueError("El corpus está vacío — no hay nada que indexar.")
    return documents


def _split_blocks(body: str) -> list[str]:
    """Parte el cuerpo en bloques por línea en blanco, y vuelve a pegar una
    línea de entrada que haya quedado huérfana de su lista.

    En el corpus actual esa fusión nunca se dispara —cada `:` ya viene en el
    mismo bloque que su lista, verificado— pero los documentos viven en
    docs/ y los edita gente de operaciones: una línea en blanco de más
    separaría "Niveles del programa:" de Bronce/Plata/Oro y degradaría la
    recuperación en silencio. Mismo criterio defensivo que
    validate_weekly_rows() en weekly_aggregation.py.
    """
    raw = [block.strip() for block in re.split(r"\n\s*\n", body) if block.strip()]

    blocks: list[str] = []
    for block in raw:
        starts_list = bool(re.match(r"^\s*(?:[-*]|\d+\.)\s", block))
        if starts_list and blocks and blocks[-1].splitlines()[-1].rstrip().endswith(":"):
            blocks[-1] = f"{blocks[-1]}\n{block}"
            continue
        blocks.append(block)
    return blocks


def _section_for(block: str, title: str) -> str:
    """Nombre de sección del chunk (CONTEXT §3: "título o subtítulo").

    Sin subtítulos en el corpus, se usa en este orden: la línea de entrada
    de la lista ("Niveles del programa:"), un rótulo corto en línea al
    abrir un párrafo ("Regla de stock mínimo: ningún local..."), o el
    título del documento para los párrafos sueltos e introductorios.
    """
    first_line = block.splitlines()[0].rstrip()
    if first_line.endswith(":"):
        return first_line[:-1].strip()

    label, separator, _ = first_line.partition(":")
    if separator and len(label.split()) <= 6:
        return label.strip()

    return title


def chunk_document(text: str, source_document: str) -> list[dict]:
    """Parte un documento en chunks autocontenidos con el payload del CONTEXT §3.

    Cada `text` se prefija con la ruta de contexto `<documento> > <sección>`:
    sin subtítulos en el original, es lo que permite que un chunk siga
    teniendo sentido cuando llega solo al prompt de generación.
    """
    lines = text.strip().splitlines()
    title = lines[0].lstrip("#").strip() if lines and lines[0].startswith("#") else source_document
    body = "\n".join(lines[1:]).strip() if lines and lines[0].startswith("#") else text.strip()

    chunks = []
    for index, block in enumerate(_split_blocks(body)):
        section = _section_for(block, title)
        prefix = title if section == title else f"{title} > {section}"
        chunks.append(
            {
                "company": COMPANY,
                "source_document": source_document,
                "section": section,
                "language": LANGUAGE,
                "chunk_index": index,
                "text": f"{prefix}\n\n{block}",
            }
        )
    return chunks


def normalize(text: str) -> str:
    """Normalización mínima antes de embeber — la misma al indexar y al
    consultar, para que la pregunta y los chunks pasen por el mismo
    preprocesado. Colapsa espacios y saltos de línea; no toca acentos ni
    mayúsculas (el modelo de embeddings los maneja y en español acentuar
    distingue palabras)."""
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------------------------------
# Embeddings e indexación — tocan red. Clientes perezosos para que importar
# este módulo (en los tests) no exija credenciales.
# --------------------------------------------------------------------------


def _openai() -> "object":
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI

        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Falta LLM_API_KEY en el entorno — necesaria para embeber y generar."
            )
        _openai_client = OpenAI(api_key=api_key, base_url=os.environ.get("LLM_BASE_URL") or None)
    return _openai_client


def _qdrant() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))
    return _qdrant_client


def embed(text: str) -> list[float]:
    """Vector de un texto con el modelo de embeddings dedicado.

    Es el único punto del sistema que llama al modelo de embeddings, y lo
    usan tanto setup() (para cada chunk) como retrieve() (para la pregunta).
    Nunca usa GENERATION_MODEL: son IDs distintos a propósito.
    """
    model = os.environ.get("EMBEDDING_MODEL")
    if not model:
        raise RuntimeError("Falta EMBEDDING_MODEL en el entorno.")

    response = _openai().embeddings.create(model=model, input=normalize(text))
    return list(response.data[0].embedding)


def _point_id(source_document: str, chunk_index: int) -> str:
    """ID determinista por (documento, posición) — no incluye el texto.

    Así, reindexar un documento editado SOBREESCRIBE el punto en vez de
    crear uno nuevo y dejar el viejo huérfano en la colección.
    """
    return str(uuid.uuid5(_ID_NAMESPACE, f"{source_document}:{chunk_index}"))


def _ensure_collection(client: QdrantClient, dimension: int) -> None:
    """Crea la colección, o la recrea si la dimensión del modelo cambió."""
    if client.collection_exists(COLLECTION_NAME):
        info = client.get_collection(COLLECTION_NAME)
        current = info.config.params.vectors.size
        if current == dimension:
            return
        print(f"  dimensión cambió ({current} -> {dimension}); recreando la colección")
        client.delete_collection(COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE),
    )


def setup() -> int:
    """Indexa el corpus completo en Qdrant. Devuelve el número de chunks.

    Idempotente: los IDs son deterministas por (source_document,
    chunk_index) y se hace upsert, así que volver a ejecutarlo no duplica
    puntos. Además, si un documento encoge, se borran los puntos sobrantes
    de ese documento — no quedan restos de la corrida anterior.
    """
    documents = load_documents()

    chunks_by_document = {}
    for document in documents:
        chunks = chunk_document(document["text"], document["source_document"])
        if len(chunks) < MIN_CHUNKS_PER_DOCUMENT:
            raise ValueError(
                f"{document['source_document']} produjo {len(chunks)} chunks; el "
                f"CONTEXT §5 exige al menos {MIN_CHUNKS_PER_DOCUMENT}."
            )
        chunks_by_document[document["source_document"]] = chunks

    all_chunks = [chunk for chunks in chunks_by_document.values() for chunk in chunks]
    print(f"Embebiendo {len(all_chunks)} chunks con {os.environ.get('EMBEDDING_MODEL')}...")
    vectors = [embed(chunk["text"]) for chunk in all_chunks]

    client = _qdrant()
    _ensure_collection(client, len(vectors[0]))

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=_point_id(chunk["source_document"], chunk["chunk_index"]),
                vector=vector,
                payload=chunk,
            )
            for chunk, vector in zip(all_chunks, vectors)
        ],
    )

    # Limpieza de sobrantes: si un documento tiene hoy menos chunks que en
    # una corrida anterior, sus puntos de cola quedarían huérfanos.
    for source_document, chunks in chunks_by_document.items():
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.Filter(
                must=[
                    models.FieldCondition(
                        key="source_document", match=models.MatchValue(value=source_document)
                    ),
                    models.FieldCondition(
                        key="chunk_index", range=models.Range(gte=len(chunks))
                    ),
                ]
            ),
        )

    for source_document, chunks in sorted(chunks_by_document.items()):
        print(f"  {source_document:20s} {len(chunks)} chunks")
    print(f"Colección '{COLLECTION_NAME}': {len(all_chunks)} chunks indexados.")
    return len(all_chunks)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    setup()
