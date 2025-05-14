uvicorn generation:app --host 0.0.0.0 --port 8080 &
python app.py --server.port 7860 --server.address 0.0.0.0
wait
