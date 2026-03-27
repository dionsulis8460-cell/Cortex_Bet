import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);

  // Construct URL for the Python Microservice
  const type = searchParams.get("type") || "predictions";
  const date = searchParams.get("date") || "today";
  const league = searchParams.get("league") || "all";
  const status = searchParams.get("status") || "all";
  const top7Only = searchParams.get("top7Only") || "false";
  const sortBy = searchParams.get("sortBy") || "confidence";

  const microserviceUrl = `http://127.0.0.1:8000/api/predictions?date=${date}&league=${league}&status=${status}&top7_only=${top7Only}&sort_by=${sortBy}`;

  try {
    // Call the persistent Python server (FastAPI)
    // This removes the 2-second overhead of spawning a new process
    const response = await fetch(microserviceUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Microservice Error:", errorText);
      throw new Error(
        `Backend Service Error (${response.status}): ${errorText}`,
      );
    }

    const data = await response.json();

    return NextResponse.json({
      success: true,
      matches: data,
    });
  } catch (error: any) {
    console.error("Error connecting to Prediction Engine:", error);

    // Fallback or friendly error
    return NextResponse.json(
      {
        success: false,
        error:
          error.message ||
          "Failed to connect to Prediction Engine. Is the server running?",
        matches: [],
      },
      { status: 500 },
    );
  }
}
