import sys
sys.path.insert(0, 'python')
from database import get_db
db = get_db()
for s in ['fixed_size', 'sentence', 'semantic']:
    count = db['document_chunks'].count_documents({'estrategia_chunking': s})
    print(f'  {s}: {count} chunks')
total = db['document_chunks'].count_documents({})
print(f'  TOTAL: {total} chunks')
