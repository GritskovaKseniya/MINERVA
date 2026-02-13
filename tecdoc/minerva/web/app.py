"""Applicazione web Flask per Minerva."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from minerva.config.settings import MinervaConfig, load_config
from minerva.database.migrations import get_connection, init_database, sync_aree_from_config
from minerva.database.repository import (
    ClienteRepository,
    DocumentRepository,
    LookupRepository,
)

logger = logging.getLogger(__name__)


def create_app(config: MinervaConfig | None = None) -> Flask:
    """Crea e configura l'applicazione Flask."""
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )

    if config is None:
        config = load_config()

    app.config["MINERVA"] = config
    app.config["SECRET_KEY"] = "minerva-dev-key"

    # Helper per colorazione righe nella tabella
    def _row_class(doc: dict) -> str:
        if doc.get("stato") == "CAN":
            return "row-can"
        classif = doc.get("classificazione", "Non Classificato")
        attivo = doc.get("attivo", 0)
        if classif == "Classificato":
            return "row-cl-si" if attivo else "row-cl-no"
        if classif == "Parzialmente Classificato":
            return "row-pc-si" if attivo else "row-pc-no"
        return "row-nc-si" if attivo else "row-nc-no"

    app.jinja_env.globals["_row_class"] = _row_class

    # Inizializza DB
    conn = init_database(config.database.path)

    # Sincronizza aree da config
    if config.classificazione.aree:
        sync_aree_from_config(
            conn, [(a.codice, a.descrizione) for a in config.classificazione.aree]
        )
        conn.commit()
    conn.close()

    def get_db():
        return get_connection(config.database.path)

    # --- ROUTES ---

    @app.route("/")
    def index():
        return redirect(url_for("documents_list"))

    @app.route("/documents")
    def documents_list():
        conn = get_db()
        try:
            doc_repo = DocumentRepository(conn)
            lookup_repo = LookupRepository(conn)
            cliente_repo = ClienteRepository(conn)

            # Parametri filtro dalla query string
            cliente = request.args.get("cliente", "")
            titolo = request.args.get("titolo", "")
            contenuto = request.args.get("contenuto", "")
            stato = request.args.get("stato", "")
            classificazione = request.args.get("classificazione", "")
            attivo = request.args.get("attivo", "")
            id_area = request.args.get("id_area", "", type=str)
            id_settore = request.args.get("id_settore", "", type=str)
            directory = request.args.get("directory", "")
            page = request.args.get("page", 1, type=int)
            per_page = request.args.get("per_page", config.web.results_per_page, type=int)

            # Cerca documenti
            results, total = doc_repo.search_documents(
                cliente=cliente or None,
                titolo=titolo or None,
                contenuto=contenuto or None,
                stato=stato or None,
                classificazione=classificazione or None,
                attivo=int(attivo) if attivo != "" else None,
                id_area=int(id_area) if id_area else None,
                id_settore=int(id_settore) if id_settore else None,
                limit=per_page,
                offset=(page - 1) * per_page,
            )

            # Filtra per directory se specificata
            if directory and results:
                results = [r for r in results if r["percorso_relativo"].startswith(directory)]

            # Conteggio revisioni per ogni documento principale
            rev_counts = doc_repo.get_revision_counts()
            for doc in results:
                doc["_rev_count"] = rev_counts.get(doc["id_documento"], 0)
                if doc["_rev_count"] > 0:
                    doc["_revisions"] = doc_repo.get_revisions_for_document(doc["id_documento"])
                else:
                    doc["_revisions"] = []

            # Dati per i filtri
            clienti = doc_repo.get_clienti()
            aree = lookup_repo.get_aree()
            settori = lookup_repo.get_settori()
            stati = lookup_repo.get_stati_documento()
            tipi_doc = lookup_repo.get_tipi_documento()
            fip_list = lookup_repo.get_fip()

            # Directory tree per il cliente selezionato
            dir_tree = []
            if cliente:
                dir_tree = doc_repo.get_directories_for_cliente(cliente)

            total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1

            return render_template(
                "documents.html",
                documents=results,
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
                clienti=clienti,
                aree=aree,
                settori=settori,
                stati=stati,
                tipi_doc=tipi_doc,
                fip_list=fip_list,
                dir_tree=dir_tree,
                # Filtri attivi
                f_cliente=cliente,
                f_titolo=titolo,
                f_contenuto=contenuto,
                f_stato=stato,
                f_classificazione=classificazione,
                f_attivo=attivo,
                f_id_area=id_area,
                f_id_settore=id_settore,
                f_directory=directory,
            )
        finally:
            conn.close()

    @app.route("/documents/<int:doc_id>")
    def document_detail(doc_id: int):
        conn = get_db()
        try:
            doc_repo = DocumentRepository(conn)
            lookup_repo = LookupRepository(conn)

            # Cerca per id
            cursor = conn.execute(
                "SELECT * FROM documenti WHERE id_documento = ?", (doc_id,)
            )
            doc = cursor.fetchone()
            if doc is None:
                abort(404)
            doc = dict(doc)

            # Classificazioni associate
            cursor = conn.execute(
                "SELECT dc.*, a.cod_area, a.descrizione as area_desc, "
                "sa.cod_sotto_area, sa.descrizione as sotto_area_desc, "
                "sua.cod_sub_area, sua.descrizione as sub_area_desc "
                "FROM documento_classificazione dc "
                "LEFT JOIN area a ON dc.id_area = a.id_area "
                "LEFT JOIN sotto_area sa ON dc.id_sotto_area = sa.id_sotto_area "
                "LEFT JOIN sub_area sua ON dc.id_sub_area = sua.id_sub_area "
                "WHERE dc.id_documento = ?",
                (doc_id,),
            )
            classificazioni = [dict(r) for r in cursor.fetchall()]

            # Tipi documento associati
            cursor = conn.execute(
                "SELECT dt.*, td.cod_tipo_documento, td.descrizione as tipo_desc "
                "FROM documento_tipo dt "
                "JOIN tipo_documento td ON dt.id_tipo_documento = td.id_tipo_documento "
                "WHERE dt.id_documento = ?",
                (doc_id,),
            )
            tipi_doc_associati = [dict(r) for r in cursor.fetchall()]

            # FIP associati
            cursor = conn.execute(
                "SELECT df.*, f.cod_fip, f.descrizione as fip_desc "
                "FROM documento_fip df "
                "JOIN fip f ON df.id_fip = f.id_fip "
                "WHERE df.id_documento = ?",
                (doc_id,),
            )
            fip_associati = [dict(r) for r in cursor.fetchall()]

            # Revisioni correlate
            revisioni = []
            if doc.get("id_documento_principale"):
                # Trova tutte le revisioni dello stesso principale
                cursor = conn.execute(
                    "SELECT * FROM documenti WHERE id_documento_principale = ? "
                    "OR id_documento = ? ORDER BY documento_revisione DESC",
                    (doc["id_documento_principale"], doc["id_documento_principale"]),
                )
                revisioni = [dict(r) for r in cursor.fetchall()]
            else:
                # Controlla se questo documento è il principale per altri
                cursor = conn.execute(
                    "SELECT * FROM documenti WHERE id_documento_principale = ? "
                    "ORDER BY documento_revisione DESC",
                    (doc_id,),
                )
                rev_list = [dict(r) for r in cursor.fetchall()]
                if rev_list:
                    revisioni = [doc] + rev_list

            # Metadati JSON
            metadati = {}
            if doc.get("metadati_json"):
                try:
                    metadati = json.loads(doc["metadati_json"])
                except json.JSONDecodeError:
                    pass

            # Lookup per i form
            aree = lookup_repo.get_aree()
            sotto_aree = lookup_repo.get_sotto_aree()
            sub_aree = lookup_repo.get_sub_aree()
            tipi_doc = lookup_repo.get_tipi_documento()
            fip_list = lookup_repo.get_fip()

            return render_template(
                "detail.html",
                doc=doc,
                classificazioni=classificazioni,
                tipi_doc_associati=tipi_doc_associati,
                fip_associati=fip_associati,
                revisioni=revisioni,
                metadati=metadati,
                aree=aree,
                sotto_aree=sotto_aree,
                sub_aree=sub_aree,
                tipi_doc=tipi_doc,
                fip_list=fip_list,
            )
        finally:
            conn.close()

    @app.route("/documents/<int:doc_id>/save", methods=["POST"])
    def document_save(doc_id: int):
        conn = get_db()
        try:
            doc_repo = DocumentRepository(conn)

            updates = {
                "classificazione": request.form.get("classificazione", "Non Classificato"),
                "attivo": 1 if request.form.get("attivo") else 0,
                "descrizione": request.form.get("descrizione", ""),
                "progetto": request.form.get("progetto", ""),
                "documento_parole_chiave": request.form.get("documento_parole_chiave", ""),
                "documento_titolo": request.form.get("documento_titolo", ""),
                "ultima_modifica_utente": "WEB_USER",
            }

            doc_repo.update_classification(doc_id, updates)

            # Aggiorna classificazioni M2M
            conn.execute("DELETE FROM documento_classificazione WHERE id_documento = ?", (doc_id,))
            area_ids = request.form.getlist("area_ids[]")
            sotto_area_ids = request.form.getlist("sotto_area_ids[]")
            sub_area_ids = request.form.getlist("sub_area_ids[]")
            for i, area_id in enumerate(area_ids):
                if area_id:
                    sa_id = sotto_area_ids[i] if i < len(sotto_area_ids) and sotto_area_ids[i] else None
                    sua_id = sub_area_ids[i] if i < len(sub_area_ids) and sub_area_ids[i] else None
                    conn.execute(
                        "INSERT INTO documento_classificazione (id_documento, id_area, id_sotto_area, id_sub_area) "
                        "VALUES (?, ?, ?, ?)",
                        (doc_id, int(area_id), int(sa_id) if sa_id else None, int(sua_id) if sua_id else None),
                    )

            # Aggiorna tipi documento M2M
            conn.execute("DELETE FROM documento_tipo WHERE id_documento = ?", (doc_id,))
            tipo_ids = request.form.getlist("tipo_ids[]")
            for tid in tipo_ids:
                if tid:
                    conn.execute(
                        "INSERT INTO documento_tipo (id_documento, id_tipo_documento) VALUES (?, ?)",
                        (doc_id, int(tid)),
                    )

            # Aggiorna FIP M2M
            conn.execute("DELETE FROM documento_fip WHERE id_documento = ?", (doc_id,))
            fip_ids = request.form.getlist("fip_ids[]")
            for fid in fip_ids:
                if fid:
                    conn.execute(
                        "INSERT INTO documento_fip (id_documento, id_fip) VALUES (?, ?)",
                        (doc_id, int(fid)),
                    )

            conn.commit()
            return redirect(url_for("document_detail", doc_id=doc_id))
        finally:
            conn.close()

    @app.route("/api/sotto_aree/<int:id_area>")
    def api_sotto_aree(id_area: int):
        conn = get_db()
        try:
            lookup = LookupRepository(conn)
            return jsonify(lookup.get_sotto_aree(id_area))
        finally:
            conn.close()

    @app.route("/api/sub_aree/<int:id_sotto_area>")
    def api_sub_aree(id_sotto_area: int):
        conn = get_db()
        try:
            lookup = LookupRepository(conn)
            return jsonify(lookup.get_sub_aree(id_sotto_area))
        finally:
            conn.close()

    @app.route("/api/directories/<cliente>")
    def api_directories(cliente: str):
        conn = get_db()
        try:
            doc_repo = DocumentRepository(conn)
            dirs = doc_repo.get_directories_for_cliente(cliente)
            return jsonify(dirs)
        finally:
            conn.close()

    @app.route("/search")
    def search():
        conn = get_db()
        try:
            doc_repo = DocumentRepository(conn)

            query = request.args.get("q", "").strip()
            cliente = request.args.get("cliente", "")
            tutte_revisioni = request.args.get("tutte_revisioni", "")
            page = request.args.get("page", 1, type=int)
            per_page = request.args.get("per_page", config.web.results_per_page, type=int)

            only_principal = tutte_revisioni != "1"

            results = []
            total = 0

            if query:
                results, total = doc_repo.fts_search(
                    query=query,
                    cliente=cliente or None,
                    only_principal=only_principal,
                    limit=per_page,
                    offset=(page - 1) * per_page,
                )

            clienti = doc_repo.get_clienti()
            total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1

            return render_template(
                "search.html",
                results=results,
                total=total,
                query=query,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
                clienti=clienti,
                f_cliente=cliente,
                f_tutte_revisioni=tutte_revisioni,
            )
        finally:
            conn.close()

    @app.route("/clienti")
    def clienti_list():
        conn = get_db()
        try:
            cliente_repo = ClienteRepository(conn)
            lookup_repo = LookupRepository(conn)
            clienti = cliente_repo.get_all()
            settori = lookup_repo.get_settori()
            return render_template("clienti.html", clienti=clienti, settori=settori)
        finally:
            conn.close()

    @app.route("/documents/<int:doc_id>/open")
    def document_open(doc_id: int):
        """Serve il file per il download/apertura nel browser."""
        conn = get_db()
        try:
            cursor = conn.execute(
                "SELECT percorso_base, percorso_relativo, documento_nome_file "
                "FROM documenti WHERE id_documento = ?",
                (doc_id,),
            )
            doc = cursor.fetchone()
            if doc is None:
                abort(404)
            doc = dict(doc)

            file_path = Path(doc["percorso_base"]) / doc["percorso_relativo"]
            if not file_path.exists():
                abort(404)

            return send_file(
                str(file_path),
                as_attachment=False,
                download_name=doc["documento_nome_file"],
            )
        finally:
            conn.close()

    @app.route("/clienti/<cliente_cartella>/settore", methods=["POST"])
    def cliente_update_settore(cliente_cartella: str):
        conn = get_db()
        try:
            cliente_repo = ClienteRepository(conn)
            id_settore = request.form.get("id_settore", type=int)
            if id_settore:
                cliente_repo.update_settore(cliente_cartella, id_settore)
                conn.commit()
            return redirect(url_for("clienti_list"))
        finally:
            conn.close()

    return app
