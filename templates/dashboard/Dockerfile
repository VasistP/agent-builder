# From-scratch observability dashboard.
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "streamlit>=1.37" "pandas>=2.2"
COPY dashboard/ dashboard/
EXPOSE 8501
CMD ["streamlit", "run", "dashboard/app.py", "--server.address=0.0.0.0"]
