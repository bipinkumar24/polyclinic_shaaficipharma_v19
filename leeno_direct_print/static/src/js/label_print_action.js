/** @odoo-module **/
import { registry } from "@web/core/registry";

/**
 * Client action that renders a label report PDF (with data payload)
 * and opens the browser print dialog.
 *
 * Expected params:
 *   report_name  – the technical report name (e.g. "product.report_producttemplatelabel2x7")
 *   data         – dict to POST as the report data
 *   title        – human-readable title for the notification
 */
async function directPrintLabelBrowser(env, action) {
    const params = action.params || {};
    const reportName = params.report_name;
    const data = params.data || {};
    const title = params.title || "Labels";

    if (!reportName) {
        env.services.notification.add("No report specified for label printing.", {
            type: "danger",
        });
        return;
    }

    // Build the URL that Odoo uses for data-driven reports.
    // The /report/pdf/ route is HTTP-type and expects data via the
    // "options" query parameter (JSON-encoded).
    const url = `/report/pdf/${reportName}?options=${encodeURIComponent(JSON.stringify(data))}`;

    const closeNotif = env.services.notification.add(
        `Preparing ${title} for printing…`,
        { type: "info", sticky: true }
    );

    try {
        // Fetch the PDF as a blob via GET
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const contentType = response.headers.get("content-type") || "";

        let blob;
        if (contentType.includes("application/pdf")) {
            blob = await response.blob();
        } else {
            // Odoo may wrap in JSON – try extracting
            const json = await response.json();
            if (json.result) {
                const byteChars = atob(json.result);
                const byteNumbers = new Array(byteChars.length);
                for (let i = 0; i < byteChars.length; i++) {
                    byteNumbers[i] = byteChars.charCodeAt(i);
                }
                blob = new Blob([new Uint8Array(byteNumbers)], {
                    type: "application/pdf",
                });
            } else {
                throw new Error("Unexpected response format");
            }
        }

        const blobUrl = URL.createObjectURL(blob);

        // Create hidden iframe and trigger print
        const iframe = document.createElement("iframe");
        iframe.style.cssText =
            "position:fixed;right:0;bottom:0;width:0;height:0;border:none;";
        document.body.appendChild(iframe);

        iframe.addEventListener("load", () => {
            setTimeout(() => {
                try {
                    if (closeNotif) closeNotif();
                    iframe.contentWindow.focus();
                    iframe.contentWindow.print();
                } catch (e) {
                    console.warn("Iframe print failed, falling back:", e);
                    const pw = window.open(blobUrl, "_blank");
                    if (pw) {
                        pw.addEventListener("load", () => {
                            pw.focus();
                            pw.print();
                        });
                    }
                }
                // Clean up after a minute
                setTimeout(() => {
                    URL.revokeObjectURL(blobUrl);
                    if (iframe.parentNode) iframe.parentNode.removeChild(iframe);
                }, 60000);
            }, 500);
        });

        iframe.addEventListener("error", () => {
            if (closeNotif) closeNotif();
            URL.revokeObjectURL(blobUrl);
            env.services.notification.add("Failed to load label PDF.", {
                type: "danger",
            });
            if (iframe.parentNode) iframe.parentNode.removeChild(iframe);
        });

        iframe.src = blobUrl;
    } catch (err) {
        if (closeNotif) closeNotif();
        console.error("Label print error:", err);

        // Fallback: use the standard report download approach
        const fallbackUrl = `/report/pdf/${reportName}?options=${encodeURIComponent(
            JSON.stringify(data)
        )}`;
        const iframe = document.createElement("iframe");
        iframe.style.cssText =
            "position:fixed;right:0;bottom:0;width:0;height:0;border:none;";
        document.body.appendChild(iframe);
        iframe.addEventListener("load", () => {
            setTimeout(() => {
                try {
                    iframe.contentWindow.focus();
                    iframe.contentWindow.print();
                } catch (e2) {
                    window.open(fallbackUrl, "_blank");
                }
                setTimeout(() => {
                    if (iframe.parentNode) iframe.parentNode.removeChild(iframe);
                }, 60000);
            }, 500);
        });
        iframe.src = fallbackUrl;
    }
}

registry
    .category("actions")
    .add("leeno_direct_print_label_browser", directPrintLabelBrowser);
