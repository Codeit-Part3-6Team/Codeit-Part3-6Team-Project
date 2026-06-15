import json

with open("notebooks/rag/rag_config_run.ipynb", "r", encoding="utf-8") as f:
    raw = f.read()

# Replace only the problematic portion of the source array
old = '# 기준안이 없을 때는 rag_keyword부터 실행합니다. 로컬 환경에서 샘플 데이터로 동작합니다.\\\n',
new = '# 기준안이 없을 때는 rag_keyword부터 실행합니다. 로컬 환경에서 샘플 데이터로 동작합니다.\n',
raw = raw.replace(old, new)

old2 = '# VM에서 실제 문서를 실험할 때는 EXP_NAME을 \\\n',
new2 = '# VM에서 실제 문서를 실험할 때는 EXP_NAME을 rag_langchain으로 바꿉니다.\n',
raw = raw.replace(old2, new2)

print(raw[:500])
with open("notebooks/rag/rag_config_run_backup.ipynb", "w", encoding="utf-8") as f:
    f.write(raw)

print("Backup saved")
