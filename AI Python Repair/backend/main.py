from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from dotenv import load_dotenv
from groq import Groq

import json
import ast
import os
import subprocess
import sys
import tempfile


# ==================================================
# ENVIRONMENT / GROQ
# ==================================================

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise RuntimeError(
        "GROQ_API_KEY is missing. "
        "Please add it to your .env file."
    )

groq_client = Groq(
    api_key=groq_api_key
)


# ==================================================
# FASTAPI
# ==================================================

app = FastAPI(
    title="AI Python Repair",
    version="1.0.0"
)


# ==================================================
# CORS
# ==================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================
# REQUEST MODELS
# ==================================================

class TestCase(BaseModel):
    input: str
    expected: str


class RunRequest(BaseModel):
    code: str
    tests: list[TestCase]


# ==================================================
# FIND FUNCTION
# ==================================================

def find_function_name(code: str):

    try:

        tree = ast.parse(code)

        for node in tree.body:

            if isinstance(node, ast.FunctionDef):
                return node.name

    except SyntaxError:

        return None

    return None


# ==================================================
# PARSE INPUT
# ==================================================

def parse_arguments(input_string: str):

    input_string = input_string.strip()

    if not input_string:
        return []

    try:

        values = ast.literal_eval(
            "(" + input_string + ",)"
        )

        return list(values)

    except Exception:

        return [
            value.strip()
            for value in input_string.split(",")
        ]


# ==================================================
# RUN SINGLE TEST
# ==================================================

def run_single_test(
    code,
    function_name,
    test_input
):

    arguments = parse_arguments(test_input)

    arguments_repr = ", ".join(
        repr(argument)
        for argument in arguments
    )

    execution_code = f"""
{code}

result = {function_name}({arguments_repr})
print(result)
"""

    temp_file = None

    try:

        # ------------------------------------------
        # CREATE TEMPORARY PYTHON FILE
        # ------------------------------------------

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        ) as file:

            file.write(execution_code)

            temp_file = file.name

        # ------------------------------------------
        # EXECUTE PYTHON PROGRAM
        # ------------------------------------------

        process = subprocess.run(
            [
                sys.executable,
                temp_file
            ],
            capture_output=True,
            text=True,
            timeout=5
        )

        # ------------------------------------------
        # RUNTIME ERROR
        # ------------------------------------------

        if process.returncode != 0:

            return {
                "passed": False,
                "output": "",
                "error": process.stderr.strip()
            }

        # ------------------------------------------
        # SUCCESSFUL EXECUTION
        # ------------------------------------------

        output = process.stdout.strip()

        return {
            "passed": True,
            "output": output,
            "error": ""
        }

    # ----------------------------------------------
    # TIMEOUT
    # ----------------------------------------------

    except subprocess.TimeoutExpired:

        return {
            "passed": False,
            "output": "",
            "error": "Execution timed out."
        }

    # ----------------------------------------------
    # OTHER ERROR
    # ----------------------------------------------

    except Exception as error:

        return {
            "passed": False,
            "output": "",
            "error": str(error)
        }

    # ----------------------------------------------
    # DELETE TEMP FILE
    # ----------------------------------------------

    finally:

        if temp_file and os.path.exists(temp_file):

            os.remove(temp_file)


# ==================================================
# EVALUATE PATCH
# ==================================================

def evaluate_patch(
    code,
    function_name,
    tests
):

    results = []

    passed_count = 0

    # ----------------------------------------------
    # RUN ALL TEST CASES
    # ----------------------------------------------

    for index, test in enumerate(tests):

        result = run_single_test(
            code,
            function_name,
            test.input
        )

        expected = test.expected.strip()

        actual = result["output"].strip()

        # ------------------------------------------
        # COMPARE OUTPUT
        # ------------------------------------------

        if result["error"]:

            passed = False

        else:

            passed = actual == expected

        if passed:

            passed_count += 1

        results.append({

            "test_number": index + 1,

            "input": test.input,

            "expected": expected,

            "actual": actual,

            "passed": passed,

            "error": result["error"]

        })

    # ----------------------------------------------
    # CALCULATE SCORE
    # ----------------------------------------------

    total_tests = len(tests)

    if total_tests > 0:

        score = round(
            (passed_count / total_tests) * 100,
            2
        )

    else:

        score = 0

    return {

        "score": score,

        "passed_tests": passed_count,

        "failed_tests": total_tests - passed_count,

        "total_tests": total_tests,

        "results": results

    }


# ==================================================
# RUN CODE API
# ==================================================

@app.post("/run")
def run_code(request: RunRequest):

    code = request.code.strip()

    # ----------------------------------------------
    # EMPTY CODE
    # ----------------------------------------------

    if not code:

        return {

            "success": False,

            "error": "No Python code provided.",

            "results": []

        }

    # ----------------------------------------------
    # SYNTAX CHECK
    # ----------------------------------------------

    try:

        ast.parse(code)

    except SyntaxError as error:

        return {

            "success": False,

            "syntax_error": True,

            "error": (
                f"SyntaxError: {error.msg} "
                f"(line {error.lineno})"
            ),

            "results": []

        }

    # ----------------------------------------------
    # FIND FUNCTION
    # ----------------------------------------------

    function_name = find_function_name(code)

    if not function_name:

        return {

            "success": False,

            "error": (
                "No Python function was found. "
                "Please define a function to test."
            ),

            "results": []

        }

    # ----------------------------------------------
    # RUN TEST CASES
    # ----------------------------------------------

    results = []

    passed_count = 0

    for index, test in enumerate(request.tests):

        result = run_single_test(

            code,

            function_name,

            test.input

        )

        expected = test.expected.strip()

        actual = result["output"].strip()

        if result["error"]:

            passed = False

        else:

            passed = actual == expected

        if passed:

            passed_count += 1

        results.append({

            "test_number": index + 1,

            "input": test.input,

            "expected": expected,

            "actual": actual,

            "passed": passed,

            "error": result["error"]

        })

    # ----------------------------------------------
    # SCORE
    # ----------------------------------------------

    total_tests = len(results)

    if total_tests > 0:

        score = round(

            (passed_count / total_tests) * 100,

            2

        )

    else:

        score = 0

    return {

        "success": True,

        "function": function_name,

        "total_tests": total_tests,

        "passed_tests": passed_count,

        "failed_tests": (
            total_tests - passed_count
        ),

        "score": score,

        "results": results

    }


# ==================================================
# HEALTH CHECK
# ==================================================

@app.get("/health")
def health():

    return {

        "status": "OK"

    }


# ==================================================
# AI REPAIR API
# ==================================================

@app.post("/repair")
def generate_repairs(request: RunRequest):

    code = request.code.strip()

    # ----------------------------------------------
    # CHECK CODE
    # ----------------------------------------------

    if not code:

        return {

            "success": False,

            "error": "No Python code provided."

        }

    # ----------------------------------------------
    # PREPARE TEST CASE INFORMATION
    # ----------------------------------------------

    test_information = []

    for index, test in enumerate(request.tests):

        test_information.append({

            "test_number": index + 1,

            "input": test.input,

            "expected_output": test.expected

        })

    # ----------------------------------------------
    # LLM PROMPT
    # ----------------------------------------------

    prompt = f"""
You are an expert Python automated program repair system.

Your task is to repair the given Python program.

The program may contain:

- Syntax errors
- Indentation errors
- Runtime errors
- Type errors
- Name errors
- Index errors
- Attribute errors
- Logical errors
- Incorrect calculations
- Incorrect conditions
- Incorrect return values

Generate exactly 5 different candidate repairs.

Each candidate must contain the COMPLETE Python program.

The candidate programs will be executed automatically
against the provided test cases.

Return ONLY valid JSON.

Use exactly this structure:

{{
    "patches": [
        {{
            "id": 1,
            "code": "complete corrected Python program"
        }},
        {{
            "id": 2,
            "code": "complete corrected Python program"
        }},
        {{
            "id": 3,
            "code": "complete corrected Python program"
        }},
        {{
            "id": 4,
            "code": "complete corrected Python program"
        }},
        {{
            "id": 5,
            "code": "complete corrected Python program"
        }}
    ]
}}

BUGGY PROGRAM:

{code}

TEST CASES:

{json.dumps(test_information, indent=2)}

IMPORTANT:

1. Return exactly 5 patches.
2. Return the complete Python program for every patch.
3. Do not return Markdown.
4. Do not use code fences.
5. Return JSON only.
6. Try to make the patches meaningfully different.
7. Preserve the intended functionality.
8. Do not modify the test cases.
"""


    # ==================================================
    # CALL GROQ
    # ==================================================

    try:

        response = groq_client.chat.completions.create(

            model="openai/gpt-oss-20b",

            messages=[

                {
                    "role": "system",

                    "content": (
                        "You are an expert Python "
                        "automated program repair "
                        "system. Return only valid JSON."
                    )

                },

                {
                    "role": "user",

                    "content": prompt

                }

            ],

            temperature=0.3

        )

        output = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

        # ------------------------------------------
        # PARSE JSON
        # ------------------------------------------

        repairs = json.loads(output)

        patches = repairs.get(
            "patches",
            []
        )

        # ==================================================
        # EVALUATE ALL PATCHES
        # ==================================================

        evaluated_patches = []

        for patch in patches:

            patch_id = patch.get("id")

            patch_code = (
                patch
                .get("code", "")
                .strip()
            )

            # ------------------------------------------
            # EMPTY PATCH
            # ------------------------------------------

            if not patch_code:

                evaluated_patches.append({

                    "id": patch_id,

                    "code": patch_code,

                    "score": 0,

                    "passed_tests": 0,

                    "failed_tests": len(
                        request.tests
                    ),

                    "total_tests": len(
                        request.tests
                    ),

                    "results": [],

                    "error": "Empty patch."

                })

                continue

            # ------------------------------------------
            # PATCH SYNTAX CHECK
            # ------------------------------------------

            try:

                ast.parse(patch_code)

            except SyntaxError as error:

                evaluated_patches.append({

                    "id": patch_id,

                    "code": patch_code,

                    "score": 0,

                    "passed_tests": 0,

                    "failed_tests": len(
                        request.tests
                    ),

                    "total_tests": len(
                        request.tests
                    ),

                    "results": [],

                    "error": (
                        f"SyntaxError: "
                        f"{error.msg} "
                        f"(line {error.lineno})"
                    )

                })

                continue

            # ------------------------------------------
            # FIND FUNCTION
            # ------------------------------------------

            function_name = find_function_name(
                patch_code
            )

            if not function_name:

                evaluated_patches.append({

                    "id": patch_id,

                    "code": patch_code,

                    "score": 0,

                    "passed_tests": 0,

                    "failed_tests": len(
                        request.tests
                    ),

                    "total_tests": len(
                        request.tests
                    ),

                    "results": [],

                    "error": (
                        "No Python function found."
                    )

                })

                continue

            # ------------------------------------------
            # EVALUATE PATCH
            # ------------------------------------------

            evaluation = evaluate_patch(

                patch_code,

                function_name,

                request.tests

            )

            evaluated_patches.append({

                "id": patch_id,

                "code": patch_code,

                "score": evaluation[
                    "score"
                ],

                "passed_tests": evaluation[
                    "passed_tests"
                ],

                "failed_tests": evaluation[
                    "failed_tests"
                ],

                "total_tests": evaluation[
                    "total_tests"
                ],

                "results": evaluation[
                    "results"
                ],

                "error": ""

            })

        # ==================================================
        # SORT PATCHES
        # ==================================================

        evaluated_patches.sort(

            key=lambda patch: patch[
                "score"
            ],

            reverse=True

        )

        # ==================================================
        # SELECT BEST PATCH
        # ==================================================

        if evaluated_patches:

            best_patch = (
                evaluated_patches[0]
            )

            other_patches = (
                evaluated_patches[1:]
            )

        else:

            best_patch = None

            other_patches = []

        # ==================================================
        # RETURN RESULT
        # ==================================================

        return {

            "success": True,

            "best_patch": best_patch,

            "other_patches": other_patches,

            "total_patches": len(
                evaluated_patches
            )

        }

    # ==================================================
    # INVALID JSON
    # ==================================================

    except json.JSONDecodeError:

        return {

            "success": False,

            "error": (
                "Groq returned invalid JSON."
            ),

            "raw_response": output

        }

    # ==================================================
    # OTHER ERROR
    # ==================================================

    except Exception as error:

        return {

            "success": False,

            "error": str(error)

        }


# ==================================================
# SERVE FRONTEND
# ==================================================
# IMPORTANT:
# This MUST remain AFTER all API routes.
# Otherwise "/" can intercept API routes.

frontend_path = os.path.join(

    os.path.dirname(
        os.path.dirname(__file__)
    ),

    "frontend"

)

app.mount(

    "/",

    StaticFiles(

        directory=frontend_path,

        html=True

    ),

    name="frontend"

)