const codeEditor = document.getElementById("codeEditor");

const testCases = document.getElementById("testCases");

const addTestBtn = document.getElementById("addTestBtn");

const clearCodeBtn = document.getElementById("clearCodeBtn");

const runBtn = document.getElementById("runBtn");

const repairBtn = document.getElementById("repairBtn");

const testResults = document.getElementById("testResults");


// -----------------------------
// ADD TEST CASE
// -----------------------------

addTestBtn.addEventListener("click", () => {

    const count =
        testCases.querySelectorAll(".test-case").length + 1;

    const test = document.createElement("div");

    test.className = "test-case";

    test.innerHTML = `
        <div class="test-title">
            <span>Test Case ${count}</span>

            <button class="remove-test">
                ×
            </button>
        </div>

        <label>Input</label>

        <input
            type="text"
            class="test-input"
            placeholder="Example: 5, 3"
        >

        <label>Expected Output</label>

        <input
            type="text"
            class="test-output"
            placeholder="Example: 8"
        >
    `;

    testCases.appendChild(test);

});


// -----------------------------
// REMOVE TEST CASE
// -----------------------------

testCases.addEventListener("click", (event) => {

    if (!event.target.classList.contains("remove-test")) {
        return;
    }

    event.target.closest(".test-case").remove();

    updateTestNumbers();

});


function updateTestNumbers() {

    const tests =
        testCases.querySelectorAll(".test-case");

    tests.forEach((test, index) => {

        test.querySelector(".test-title span")
            .textContent = `Test Case ${index + 1}`;

    });

}


// -----------------------------
// CLEAR CODE
// -----------------------------

clearCodeBtn.addEventListener("click", () => {

    codeEditor.value = "";

    testResults.innerHTML = `
        <div class="empty-state">
            Enter your Python program.
        </div>
    `;

});


// -----------------------------
// COLLECT TEST CASES
// -----------------------------

function collectTestCases() {

    const tests =
        testCases.querySelectorAll(".test-case");

    const data = [];

    tests.forEach(test => {

        const input =
            test.querySelector(".test-input").value;

        const expected =
            test.querySelector(".test-output").value;

        data.push({
            input: input,
            expected: expected
        });

    });

    return data;

}


// -----------------------------
// RUN CODE
// -----------------------------

runBtn.addEventListener("click", async () => {

    const code = codeEditor.value;

    const tests = collectTestCases();

    if (!code.trim()) {

        alert("Please enter Python code.");

        return;
    }

    testResults.innerHTML = `
        <div class="empty-state">
            ⏳ Running tests...
        </div>
    `;

    try {

        const response = await fetch(
    "/run",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    code: code,
                    tests: tests
                })
            }
        );

        const result = await response.json();

        displayTestResults(result);

    } catch (error) {

        testResults.innerHTML = `
            <div class="test-result">
                <span class="test-fail">
                    Backend connection failed.
                </span>
            </div>
        `;

        console.error(error);

    }

});


// -----------------------------
// DISPLAY RESULTS
// -----------------------------

function displayTestResults(result) {

    if (!result.results) {

        testResults.innerHTML = `
            <div class="test-result">
                <span class="test-fail">
                    ${result.error || "Unknown error"}
                </span>
            </div>
        `;

        return;
    }


    testResults.innerHTML = `

        <div class="test-summary">

            <strong>
                Score: ${result.score}%
            </strong>

            <span>
                Passed: ${result.passed_tests}
                /
                ${result.total_tests}
            </span>

        </div>

    `;


    result.results.forEach((test, index) => {

        const div =
            document.createElement("div");

        div.className = "test-result";

        div.innerHTML = `

            <div>

                <strong>
                    Test Case ${index + 1}
                </strong>

                <div style="font-size: 12px; margin-top: 6px; color: #9299a6;">

                    Expected:
                    ${escapeHtml(test.expected)}

                    &nbsp; | &nbsp;

                    Actual:
                    ${escapeHtml(test.actual)}

                </div>

                ${
                    test.error
                        ? `
                            <div
                                style="
                                    font-size: 12px;
                                    margin-top: 6px;
                                    color: #ff7070;
                                "
                            >
                                ${escapeHtml(test.error)}
                            </div>
                        `
                        : ""
                }

            </div>


            <span class="${
                test.passed
                    ? "test-pass"
                    : "test-fail"
            }">

                ${
                    test.passed
                        ? "✓ PASS"
                        : "✗ FAIL"
                }

            </span>

        `;

        testResults.appendChild(div);

    });

}


function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


// -----------------------------
// AI REPAIR
// -----------------------------

repairBtn.addEventListener("click", () => {

    alert(
        "AI Repair will be connected after the Python test runner is complete."
    );

});