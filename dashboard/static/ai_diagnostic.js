/* =========================================================
   AI DIAGNOSTIC EXPLANATION
   Knowledge-Driven IoT Fault Diagnosis Assistant
========================================================= */

"use strict";


/* =========================================================
   START AI ANALYSIS
========================================================= */

async function runAIDiagnosis() {

    const button =
        document.getElementById(
            "runAIButton"
        );


    const result =
        document.getElementById(
            "aiResult"
        );


    if (
        !button ||
        !result
    ) {
        return;
    }


    button.disabled =
        true;


    button.textContent =
        "Analyzing...";


    result.innerHTML =
        `
        <div class="ai-loading">

            Retrieving project knowledge,
            current telemetry and rule-based
            findings...

        </div>
        `;


    try {

        const response =
            await fetch(
                "/api/ai-diagnosis",
                {
                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({})
                }
            );


        let data;


        try {

            data =
                await response.json();

        }
        catch (
            parseError
        ) {

            throw new Error(
                "The server returned an invalid response."
            );
        }


        if (
            !response.ok
        ) {

            throw new Error(
                data.error ||
                "AI diagnosis request failed."
            );
        }


        /*
           The backend may return:

           {
               diagnosis: "..."
           }

           or:

           {
               diagnosis: {
                   answer: "..."
               }
           }

           or:

           {
               answer: "..."
           }
        */


        let diagnosis =
            data.diagnosis;


        if (
            diagnosis &&
            typeof diagnosis ===
                "object"
        ) {

            diagnosis =
                diagnosis.answer ||
                diagnosis.diagnosis ||
                diagnosis.response ||
                diagnosis.result ||
                "";
        }


        if (
            !diagnosis &&
            data.answer
        ) {

            diagnosis =
                data.answer;
        }


        if (
            !diagnosis &&
            data.response
        ) {

            diagnosis =
                data.response;
        }


        if (
            !diagnosis &&
            data.result
        ) {

            diagnosis =
                data.result;
        }


        if (
            !diagnosis
        ) {

            throw new Error(
                "No AI diagnosis was returned by the backend."
            );
        }


        result.innerHTML =
            formatAIText(
                diagnosis
            );

    }
    catch (
        error
    ) {

        console.error(
            "AI diagnosis error:",
            error
        );


        result.innerHTML =
            `
            <div class="ai-error">

                <strong>
                    AI analysis failed.
                </strong>

                <br>
                <br>

                ${escapeHTML(
                    error.message
                )}

            </div>
            `;

    }
    finally {

        button.disabled =
            false;


        button.textContent =
            "Run AI Analysis";
    }
}


/* =========================================================
   FORMAT AI RESPONSE
========================================================= */

function formatAIText(
    text
) {

    let escaped =
        escapeHTML(
            text
        );


    /*
       Headings
    */

    escaped =
        escaped.replace(
            /^### (.+)$/gm,
            "<h4>$1</h4>"
        );


    escaped =
        escaped.replace(
            /^## (.+)$/gm,
            "<h3>$1</h3>"
        );


    escaped =
        escaped.replace(
            /^# (.+)$/gm,
            "<h3>$1</h3>"
        );


    /*
       Bold
    */

    escaped =
        escaped.replace(
            /\*\*(.*?)\*\*/g,
            "<strong>$1</strong>"
        );


    /*
       Bullet points
    */

    escaped =
        escaped.replace(
            /^[•*-]\s+(.+)$/gm,
            "<div class=\"ai-bullet\">• $1</div>"
        );


    /*
       Numbered items
    */

    escaped =
        escaped.replace(
            /^(\d+)\.\s+(.+)$/gm,
            "<div class=\"ai-numbered\"><strong>$1.</strong> $2</div>"
        );


    /*
       New lines
    */

    escaped =
        escaped.replace(
            /\n/g,
            "<br>"
        );


    return `
        <div class="ai-answer">
            ${escaped}
        </div>
    `;
}


/* =========================================================
   HTML ESCAPE
========================================================= */

function escapeHTML(
    value
) {

    const div =
        document.createElement(
            "div"
        );


    div.textContent =
        value ?? "";


    return div.innerHTML;
}


/* =========================================================
   BUTTON EVENT
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        const button =
            document.getElementById(
                "runAIButton"
            );


        if (
            button
        ) {

            button.addEventListener(
                "click",
                runAIDiagnosis
            );
        }
    }
);