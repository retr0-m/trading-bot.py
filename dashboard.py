from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# We'll store portfolio data here for now
portfolio = {
    "balance": 10000,
    "positions": [],
    "equity": 10000
}

@app.get("/")
def read_dashboard():
    html_content = f"""
    <html>
        <head>
            <title>Trading Bot Dashboard</title>
        </head>
        <body>
            <h1>Portfolio</h1>
            <p>Balance: ${portfolio['balance']}</p>
            <p>Equity: ${portfolio['equity']}</p>
            <h2>Positions</h2>
            <ul>
                {''.join([f"<li>{pos}</li>" for pos in portfolio['positions']])}
            </ul>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)