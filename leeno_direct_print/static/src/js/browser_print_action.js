/** @odoo-module **/
import { registry } from "@web/core/registry";

async function directPrintBrowser(env, action) {
    const params = action.params || {};
    const url = params.url;
    if (!url) {
        env.services.notification.add(
            "No PDF URL provided for browser printing.",
            { type: "danger" }
        );
        return;
    }
    const iframe = document.createElement("iframe");
    iframe.style.position = "fixed";
    iframe.style.right = "0";
    iframe.style.bottom = "0";
    iframe.style.width = "0";
    iframe.style.height = "0";
    iframe.style.border = "none";
    document.body.appendChild(iframe);
    const closeNotif = env.services.notification.add(
        "Preparing document for printing...",
        { type: "info", sticky: true }
    );
    iframe.addEventListener("load", () => {
        setTimeout(() => {
            try {
                if (closeNotif) closeNotif();
                iframe.contentWindow.focus();
                iframe.contentWindow.print();
            } catch (e) {
                console.warn("Iframe print failed, falling back to window.open:", e);
                const pw = window.open(url, "_blank");
                if (pw) {
                    pw.addEventListener("load", () => {
                        pw.focus();
                        pw.print();
                    });
                }
            }
            setTimeout(() => {
                if (iframe.parentNode) iframe.parentNode.removeChild(iframe);
            }, 60000);
        }, 500);
    });
    iframe.addEventListener("error", () => {
        if (closeNotif) closeNotif();
        env.services.notification.add(
            "Failed to load the PDF for printing.",
            { type: "danger" }
        );
        if (iframe.parentNode) iframe.parentNode.removeChild(iframe);
    });
    iframe.src = url;
}

registry.category("actions").add("leeno_direct_print_browser", directPrintBrowser);

