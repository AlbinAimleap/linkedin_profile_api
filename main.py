if __name__ == "__main__":
    import uvicorn
    uvicorn.run("linkedin_search.api:app", host="0.0.0.0", port=8000, reload=True)
