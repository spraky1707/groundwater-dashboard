/* ============================================================
   GROUNDWATER TREND
   REAL DATA ONLY
   ============================================================ */

let trendChart = null;


/* ============================================================
   FIND TREND CANVAS
   ============================================================ */

function getTrendCanvas() {

    const possibleIds = [
        "groundwaterTrend",
        "trendChart",
        "groundwaterChart",
        "historyChart"
    ];

    for (const id of possibleIds) {

        const element =
            document.getElementById(id);

        if (element) {
            return element;
        }
    }

    return null;
}


/* ============================================================
   CLEAR CHART
   ============================================================ */

function clearTrendChart() {

    if (trendChart) {

        try {
            trendChart.destroy();
        } catch (error) {
            console.warn(
                "Unable to destroy previous chart:",
                error
            );
        }

        trendChart = null;
    }
}


/* ============================================================
   TREND MESSAGE
   ============================================================ */

function showTrendMessage(message) {

    const canvas =
        getTrendCanvas();

    if (!canvas) {
        return;
    }

    const parent =
        canvas.parentElement;

    if (!parent) {
        return;
    }

    let messageElement =
        parent.querySelector(
            ".trend-empty-message"
        );

    if (!messageElement) {

        messageElement =
            document.createElement("div");

        messageElement.className =
            "trend-empty-message";

        messageElement.style.textAlign =
            "center";

        messageElement.style.padding =
            "24px";

        messageElement.style.fontSize =
            "14px";

        messageElement.style.opacity =
            "0.75";

        parent.appendChild(
            messageElement
        );
    }

    messageElement.textContent =
        message;

    messageElement.style.display =
        "block";
}


/* ============================================================
   HIDE TREND MESSAGE
   ============================================================ */

function hideTrendMessage() {

    const canvas =
        getTrendCanvas();

    if (!canvas) {
        return;
    }

    const parent =
        canvas.parentElement;

    if (!parent) {
        return;
    }

    const messageElement =
        parent.querySelector(
            ".trend-empty-message"
        );

    if (messageElement) {

        messageElement.style.display =
            "none";
    }
}


/* ============================================================
   UPDATE HISTORY COUNT
   ============================================================ */

function updateHistoryCount(count) {

    const ids = [
        "historyCount",
        "trendCount"
    ];

    ids.forEach(id => {

        const element =
            document.getElementById(id);

        if (!element) {
            return;
        }

        if (count === 1) {

            element.textContent =
                "1 observation";

        } else {

            element.textContent =
                `${count} observations`;
        }
    });
}


/* ============================================================
   LOAD HISTORY
   ============================================================ */

async function loadHistory() {

    const canvas =
        getTrendCanvas();

    if (!canvas) {

        console.warn(
            "Groundwater trend canvas not found."
        );

        return;
    }


    clearTrendChart();

    hideTrendMessage();


    try {

        const params =
            getLocationParameters();


        /*
         * Do not request history until
         * at least a state is selected.
         */

        if (!params.state) {

            showTrendMessage(
                "Select a location to view groundwater history."
            );

            return;
        }


        const data =
            await fetchJSON(
                apiURL(
                    "/api/history",
                    params
                )
            );


        console.log(
            "REAL HISTORY DATA:",
            data
        );


        const rawLabels =
            Array.isArray(data.labels)
                ? data.labels
                : [];


        const rawValues =
            Array.isArray(data.values)
                ? data.values
                : [];


        /*
         * ------------------------------------------------------
         * IMPORTANT:
         * Build the points using the backend arrays.
         *
         * No artificial points.
         * No random values.
         * No interpolation.
         * ------------------------------------------------------
         */

        const points = [];

        const length =
            Math.min(
                rawLabels.length,
                rawValues.length
            );


        for (
            let i = 0;
            i < length;
            i++
        ) {

            const numericValue =
                Number(
                    rawValues[i]
                );


            if (
                !Number.isFinite(
                    numericValue
                )
            ) {
                continue;
            }


            const label =
                String(
                    rawLabels[i]
                ).trim();


            if (!label) {
                continue;
            }


            points.push({

                label:
                    label,

                value:
                    numericValue

            });
        }


        updateHistoryCount(
            points.length
        );


        /* ------------------------------------------------------
           NO DATA
           ------------------------------------------------------ */

        if (points.length === 0) {

            showTrendMessage(
                data.message ||
                "No historical groundwater observations available for the selected location."
            );

            return;
        }


        hideTrendMessage();


        const labels =
            points.map(
                point => point.label
            );


        const values =
            points.map(
                point => point.value
            );


        /* ------------------------------------------------------
           CHECK CHART.JS
           ------------------------------------------------------ */

        if (
            typeof Chart ===
            "undefined"
        ) {

            console.error(
                "Chart.js is not loaded."
            );

            showTrendMessage(
                "Chart.js is not loaded."
            );

            return;
        }


        /* ------------------------------------------------------
           CANVAS
           ------------------------------------------------------ */

        canvas.style.display =
            "block";

        canvas.style.width =
            "100%";

        canvas.style.height =
            "320px";


        /*
         * Remove stale dimensions that can sometimes
         * make Chart.js render incorrectly.
         */

        canvas.removeAttribute(
            "width"
        );

        canvas.removeAttribute(
            "height"
        );


        /* ------------------------------------------------------
           REAL LINE CHART
           ------------------------------------------------------ */

        const context =
            canvas.getContext(
                "2d"
            );


        trendChart =
            new Chart(
                context,
                {

                    type:
                        "line",


                    data: {

                        labels:
                            labels,

                        datasets: [

                            {

                                label:
                                    "Groundwater Depth",

                                data:
                                    values,


                                /*
                                 * THIS IS THE IMPORTANT PART.
                                 *
                                 * With 2+ genuine records,
                                 * Chart.js draws a real line.
                                 */

                                showLine:
                                    true,

                                fill:
                                    false,

                                tension:
                                    0.25,

                                spanGaps:
                                    false,


                                borderWidth:
                                    3,

                                borderColor:
                                    "#38bdf8",


                                pointRadius:
                                    points.length === 1
                                        ? 7
                                        : 4,

                                pointHoverRadius:
                                    8,

                                pointBackgroundColor:
                                    "#38bdf8",

                                pointBorderColor:
                                    "#ffffff",

                                pointBorderWidth:
                                    2

                            }

                        ]

                    },


                    options: {

                        responsive:
                            true,

                        maintainAspectRatio:
                            false,


                        /*
                         * Don't let Chart.js
                         * animate the line from a
                         * single visible dot in a
                         * confusing way.
                         */

                        animation:
                            points.length > 1
                                ? {
                                    duration: 700,
                                    easing:
                                        "easeOutQuart"
                                }
                                : false,


                        interaction: {

                            mode:
                                "index",

                            intersect:
                                false

                        },


                        plugins: {

                            legend: {

                                display:
                                    true,

                                labels: {

                                    usePointStyle:
                                        true,

                                    padding:
                                        18

                                }

                            },


                            tooltip: {

                                enabled:
                                    true,

                                callbacks: {

                                    label:
                                        function(context) {

                                            const value =
                                                context.parsed.y;

                                            return (
                                                " Groundwater Depth: "
                                                +
                                                Number(value)
                                                    .toFixed(2)
                                                +
                                                " m"
                                            );
                                        }

                                }

                            }

                        },


                        scales: {

                            x: {

                                display:
                                    true,

                                title: {

                                    display:
                                        true,

                                    text:
                                        "Observation Date"

                                },

                                grid: {

                                    display:
                                        false

                                }

                            },


                            y: {

                                display:
                                    true,

                                beginAtZero:
                                    false,

                                title: {

                                    display:
                                        true,

                                    text:
                                        "Groundwater Depth (m)"

                                },

                                ticks: {

                                    callback:
                                        function(value) {

                                            return (
                                                value +
                                                " m"
                                            );
                                        }

                                }

                            }

                        }

                    }

                }
            );


        /*
         * ------------------------------------------------------
         * ONE RECORD NOTICE
         * ------------------------------------------------------
         */

        if (points.length === 1) {

            showTrendMessage(
                "Only one historical observation is available for this selected location."
            );

            /*
             * Keep the chart visible.
             * The message explains why there is no line.
             */

        } else {

            hideTrendMessage();
        }


        console.log(
            `Groundwater trend rendered with ${points.length} real observations.`
        );


    } catch (error) {

        console.error(
            "Groundwater history loading failed:",
            error
        );

        clearTrendChart();

        showTrendMessage(
            "Unable to load groundwater history."
        );

    }

}