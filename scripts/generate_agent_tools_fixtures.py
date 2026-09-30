"""Fixtures explícitamente simuladas; los evals no ejecutan el grafo."""
import argparse
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services/api'))
from support_agent.service import open_service
from support_agent.contracts import Decision
from support_agent import routing
from support_agent.graph import rag
from support_agent.tools import incidents

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
manifest={'mode':'mock','cases':{}}
with tempfile.TemporaryDirectory() as runtime:
    with open_service(runtime,args.output_dir,mode='mock') as service:
        for case in ('tool','rag','fallback'):
            decision=Decision(source='rag',rag_question='¿Cuántos puntos para Oro?') if case=='rag' else Decision(source='incidents',ticket_id=482)
            result={'status':'timeout','items':[]} if case=='fallback' else {'status':'ok','total':1,'items':[{'id':482,'status':'open','category':'technical','origin':'api','updated_at':'2026-09-30T10:00:00Z','resolved_at':None}]}
            with patch.object(routing,'classify',lambda q:decision),patch.object(incidents,'lookup',lambda d:result),patch.object(rag,'retrieve',lambda q:[{'source_document':'loyalty-program','text':'Oro (50+ puntos)'}]),patch.object(rag,'generate_answer',lambda q,c:'Oro: 50 puntos.'):
                _,run=service.query('¿Cuántos puntos para Oro?' if case=='rag' else '¿En qué estado está el ticket 482?',owner='7')
                manifest['cases'][case]=f'{run}.json'
(args.output_dir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Tres trazas MOCK guardadas; no equivalen a evidencia real.')
