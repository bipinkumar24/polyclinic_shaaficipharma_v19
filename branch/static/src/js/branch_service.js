import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { UPDATE_METHODS } from "@web/core/orm_service";
import { cookie } from "@web/core/browser/cookie";
import { rpc } from '@web/core/network/rpc';
import { user } from "@web/core/user";
import { router } from "@web/core/browser/router";
import { rpcBus } from "@web/core/network/rpc";


const BIDS_HASH_SEPARATOR = "-";

function parseBranchIds(bids, separator = BIDS_HASH_SEPARATOR) {
    if (typeof bids === "string") {
        return bids.split(separator).map(Number);
    } else if (typeof bids === "number") {
        return [bids];
    }
    return [];
}

function formatBranchIds(bids, separator = ",") {
    return bids.join(separator);
}

function computeActiveBranchIds(bids) {
    const { user_branches } = session;
    let activeBranchIds = bids || [];
    const availableBranchesFromSession = user_branches.allowed_branches;
    const notAllowedBranches = activeBranchIds.filter(
        (id) => !(id in availableBranchesFromSession)
    );
    if (!activeBranchIds.length || notAllowedBranches.length) {
        activeBranchIds = [user_branches.current_branch];
    }
    return activeBranchIds;
}

function getBranchIdsFromBrowser(hash) {
    let bids;
    const state = router.current;

    if ("bids" in state) {
        // backward compatibility s.t. old urls (still using "," as separator) keep working
        // deprecated as of 17.0
        if (typeof state.bids === "string" && !state.bids.includes(BIDS_HASH_SEPARATOR)) {
            bids = parseBranchIds(state.bids, ",");
        } else {
            bids = parseBranchIds(state.bids);
        }
    } else if (cookie.get("bids")) {
        bids = parseBranchIds(cookie.get("bids"));
    }
    return bids || [];
}


export const BranchService = {

    dependencies: ["action", "orm"],
    start(env, { action, orm }) {
        // Push an error handler in the registry. It needs to be before "rpcErrorHandler", which
        // has a sequence of 97. The default sequence of registry is 50.

        const allowedBranches = session.user_branches.allowed_branches;
        const allowedBranchesWithAncestors = {
            ...allowedBranches,
        };
        const activeBranchIds = computeActiveBranchIds(
            getBranchIdsFromBrowser()
        );

        cookie.set("bids", activeBranchIds.join(BIDS_HASH_SEPARATOR));
        user.updateContext({ allowed_branch_ids: activeBranchIds });
        
        rpcBus.addEventListener("RPC:RESPONSE", (ev) => {
            const { data, error } = ev.detail;
            const { model, method } = data.params;
            if (!error && model === "res.branch" && UPDATE_METHODS.includes(method)) {
                if (!browser.localStorage.getItem("running_tour")) {
                    action.doAction("reload_context");
                }
            }
        });

        return {
            allowedBranches,
            allowedBranchesWithAncestors,

            get activeBranchIds() {
                return activeBranchIds.slice() || [1];
            },

            get currentBranch() {
                return allowedBranches[activeBranchIds[0]];
            },

            getBranch(BranchId) {
                return allowedBranchesWithAncestors[BranchId];
            },

            /**
             * @param {Array<>} BranchIds - List of branches to log into
             */
            async setBranches(BranchIds) {
                const newBranchIds = BranchIds.length ? BranchIds : [activeBranchIds[0]];
                function addBranches(BranchIds) {
                    for (const BranchId of BranchIds) {
                        if (!newBranchIds.includes(BranchId)) {
                            newBranchIds.push(BranchId);
                        }
                    }
                }
                cookie.set("bids", newBranchIds.join(BIDS_HASH_SEPARATOR));
                user.updateContext({ allowed_branch_ids: newBranchIds });

                rpc('/set_brnach', {BranchID: newBranchIds[0]});

                const controller = action.currentController;
                const state = {};
                const options = { reload: true };
                if (controller?.props.resId && controller?.props.resModel) {
                    const hasReadRights = await user.checkAccessRight(
                        controller.props.resModel,
                        "read",
                        controller.props.resId
                    );

                    if (!hasReadRights) {
                        options.replace = true;
                        state.actionStack = router.current.actionStack.slice(0, -1);
                    }
                }
                router.pushState(state, options);
            },
        };
    },
};
registry.category("services").add("Branch", BranchService);
