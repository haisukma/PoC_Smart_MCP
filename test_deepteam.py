import asyncio
import uuid
import os
import httpx

from deepteam.vulnerabilities import ShellInjection, ToolMetadataPoisoning
from deepeval.models import OpenRouterModel


FASTAPI_URL = "http://127.0.0.1:8000/chat"

counter = 0 

async def agentku(prompt: str) -> str:
    global counter
    counter += 1

    print(f"\n{'=' * 60}")
    print(f"TEST CASE #{counter}")
    print(f"PROMPT: {prompt}")
    print(f"{'=' * 60}")

    async with httpx.AsyncClient(timeout=None) as client:

        async with client.stream(
            "POST",
            FASTAPI_URL,
            data={
                "message": prompt,
                "thread_id": str(uuid.uuid4()),
            },
        ) as response:

            response.raise_for_status()

            result = []

            async for chunk in response.aiter_text():
                if chunk:
                    result.append(chunk)

            return "".join(result)


async def main():

    openrouter_api_key = os.environ["OPEN_ROUTER_KEY1"]

    simulator_model = OpenRouterModel(
        model="openrouter/free",
        api_key=openrouter_api_key,
    )

    evaluation_model = OpenRouterModel(
        model="openrouter/free",
        api_key=openrouter_api_key,
    )

    # shell_injection = ShellInjection(
    #     simulator_model=simulator_model,
    #     evaluation_model=evaluation_model,
    # )

    tool_metadata_poisoning = ToolMetadataPoisoning(
        simulator_model=simulator_model,
        evaluation_model=evaluation_model
    )

    result = tool_metadata_poisoning.assess(
        model_callback=agentku
    )

    # result = shell_injection.assess(
    #     model_callback=agentku
    # )

    for vuln_type, test_cases in result.items():
        print(f"\n=== {vuln_type} ===")
        print(test_cases)


if __name__ == "__main__":
    asyncio.run(main())