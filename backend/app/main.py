from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, employees, projects, tasks, reviews, queries

app = FastAPI(title="Productivity Monitor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(reviews.router)
app.include_router(queries.router)

@app.get("/")
def root():
    return {"message": "Productivity DB API is running"}