import pandas as pd
from google import genai
from config.settings import GOOGLE_API_KEY, GEMINI_MODEL

client = genai.Client(api_key=GOOGLE_API_KEY)

def process_with_pandasai(df, user_query):
    try:
        if df is None or df.empty:
            return "No data available to analyze."

        if len(df) > 500:
            df = df.head(500)

        # Build a rich description of the dataframe for Gemini
        col_info = "\n".join([
            f"- Column '{col}': sample values = {df[col].head(3).tolist()}"
            for col in df.columns
        ])

        prompt = f"""
        You are a data analyst. The following dataframe contains query results from a database.

        User Question: {user_query}

        Column descriptions (inferred from sample values):
        {col_info}

        Full data:
        {df.to_string(index=False)}

        Rules:
        - Infer what each column represents from its sample values.
        - The data above IS the answer — interpret it directly and correctly.
        - If there is only 1 row, that single value IS the answer.
        - If there are multiple rows, identify the correct one based on the question (e.g., highest, lowest, most frequent).
        - Be concise, factual, and specific. Name actual values from the data.
        - Do NOT say you cannot determine the answer if the data is clearly there.
        """

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        return response.text.strip()

    except Exception as e:
        return f"Analysis error: {str(e)}"