import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownGroup } from "@web/core/dropdown/dropdown_group";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { Component, useChildSubEnv, useRef, useState } from "@odoo/owl";
import { useCommand } from "@web/core/commands/command_hook";
import { _t } from "@web/core/l10n/translation";
import { symmetricalDifference } from "@web/core/utils/arrays";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { SwitchBranchItem } from "@branch/js/switch_branch_item";


class BranchSelector {
    constructor(BranchService, dropdownState) {
        this.BranchService = BranchService;
        this.dropdownState = dropdownState;
        this.selectedBranchesIds = BranchService.activeBranchIds.slice();
    }

    get hasSelectionChanged() {
        return (
            symmetricalDifference(this.selectedBranchesIds, this.BranchService.activeBranchIds)
                .length > 0
        );
    }


    isBranchSelected(BranchId) {
        return this.selectedBranchesIds.includes(BranchId);
    }

    switchBranch(mode, BranchId) {
        if (mode === "toggle") {
            if (this.selectedBranchesIds.includes(BranchId)) {
                this._deselectBranch(BranchId);
            } else {
                this._selectBranch(BranchId);
            }
        } else if (mode === "loginto") {
           if (this._isSingleBranchMode()) {
               this.selectedBranchesIds.splice(0, this.selectedBranchesIds.length);
           }
            this._selectBranch(BranchId, true);
            this.apply();
            this.dropdownState.close?.();
        }
    }

    _selectBranch(BranchId,unshift = false) {
        if (!this.selectedBranchesIds.includes(BranchId)) {
            if (unshift) {
                this.selectedBranchesIds.unshift(BranchId);
            } else {
                this.selectedBranchesIds.push(BranchId);
            }
        } else if (unshift) {
            const index = this.selectedBranchesIds.findIndex((b) => b === BranchId);
            this.selectedBranchesIds.splice(index, 1);
            this.selectedBranchesIds.unshift(BranchId);
        }
    }

    _deselectBranch(BranchId) {
        if (this.selectedBranchesIds.includes(BranchId)) {
            this.selectedBranchesIds.splice(this.selectedBranchesIds.indexOf(BranchId), 1);
        }
    }


    apply() {

        this.BranchService.setBranches(this.selectedBranchesIds,false);
        
    }
   _isSingleBranchMode() {
       if (this.selectedBranchesIds.length === 1) {
           return true;
       }

       const getActiveBranch = (BranchId) => {
           const isActive = this.selectedBranchesIds.includes(BranchId);
           return isActive ? this.BranchService.getBranch(BranchId) : null;
       };

       let rootBranch = undefined;
       for (const branchId of this.selectedBranchesIds) {
            let branch = getActiveBranch(branchId);

           if (rootBranch === undefined) {
               rootBranch = branch;
           } else if (rootBranch !== branch) {
               return false;
           }
       }

       return true;
   }

    reset() {
        this.selectedBranchesIds = this.BranchService.activeBranchIds.slice();
    }

    selectAll() {
        if (this.selectedBranchesIds.length > 0) {
            this.selectedBranchesIds.splice(0, this.selectedBranchesIds.length);
        } else {
            const newIds = Object.values(this.BranchService.allowedBranches).map((b) => b.id);
            this.selectedBranchesIds.splice(0, this.selectedBranchesIds.length, ...newIds);
        }
    }
}


export class SwitchBranchMenu extends Component {
    static template = "web.SwitchBranchMenu";
    static components = { Dropdown, DropdownGroup, SwitchBranchItem};
    static props = {};

    setup() {
        this.dropdown = useDropdownState();
        this.BranchService = useService("Branch");

        this.BranchSelector = useState(new BranchSelector(this.BranchService, this.dropdown));
        useChildSubEnv({ BranchSelector: this.BranchSelector });

        this.searchInputRef = useRef("inputRef");
        this.state = useState({});
        this.resetState();

        this.containerRef = useChildRef();
    }


     get hasLotsOfBranches() {
        return Object.values(this.BranchService.allowedBranchesWithAncestors).length > 9;
    }

    get branchesEntries() {
        const branches = [];

        const addBranch = (branch, level = 0) => {
            if (this.matchSearch(branch.name)) {
                branches.push({ branch, level });
            }

            if (branch.child_ids) {
                for (const branchId of branch.child_ids) {
                    addBranch(this.BranchService.getBranch(branchId), level + 1);
                }
            }
        };

        Object.values(this.BranchService.allowedBranchesWithAncestors)
            .filter((b) => !b.parent_id)
            .sort((b1, b2) => b1.sequence - b2.sequence)
            .forEach((b) => addBranch(b));
        return branches;
    }


    get selectAllClass() {
        if (
            this.BranchSelector.selectedBranchesIds.length >=
            Object.values(this.BranchService.allowedBranches).length
        ) {
            return "btn-link text-primary";
        } else {
            return "btn-link text-secondary";
        }
    }

    get selectAllIcon() {
        if (
            this.BranchSelector.selectedBranchesIds.length >=
            Object.values(this.BranchService.allowedBranches).length
        ) {
            return "fa-check-square text-primary";
        } else if (this.BranchSelector.selectedBranchesIds.length > 0) {
            return "fa-minus-square-o";
        } else {
            return "fa-square-o";
        }
    }

    resetState() {
        this.state.searchFilter = "";
        this.state.showFilter = this.hasLotsOfBranches;
    }

    onSearch(ev) {
        this.state.searchFilter = ev.target.value;
        this.state.showFilter = true;
    }

    matchSearch(bracnhName) {
        if (!this.state.searchFilter) {
            return true;
        }

        const name = bracnhName.toLocaleLowerCase().replace(/\s/g, "");
        const filter = this.state.searchFilter.toLocaleLowerCase().replace(/\s/g, "");
        return name.includes(filter);
    }

    handleDropdownChange(isOpen) {
        if (isOpen) {
            if (this.searchInputRef.el) {
                this.searchInputRef.el.focus();
            }

            if (this.containerRef.el) {
                // Fixes the container width so it doesn't change when searching.
                const currentWidth = this.containerRef.el.getBoundingClientRect().width;
                this.containerRef.el.style.width = currentWidth + "px";
            }
        } else {
            this.resetState();
        }
    }
    
    confirm() {
        this.dropdown.close();
        this.BranchSelector.apply();
    }

    get isSingleBranch() {
        return Object.values(this.BranchService.allowedBranchesWithAncestors ?? {}).length === 1;
    }

}

export const systrayItem = {
    Component: SwitchBranchMenu,
    isDisplayed(env) {
        const { allowedBranches } = env.services.Branch;
        return Object.keys(allowedBranches).length > 1;
    },
};

if (session.display_switch_branch_menu) {
    registry.category("systray").add("SwitchBranchMenu", systrayItem, { sequence: 1 });

}
