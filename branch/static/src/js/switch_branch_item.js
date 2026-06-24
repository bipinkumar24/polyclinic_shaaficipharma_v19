import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class SwitchBranchItem extends Component {
    static template = "web.SwitchBranchItem";
    static components = { DropdownItem, SwitchBranchItem };
    static props = {
        branch: {},
        level: { type: Number },
    };

    setup() {
        this.BranchService = useService("Branch");
        this.BranchSelector = useState(this.env.BranchSelector);
    }
    
    get isBranchSelected() {
        return this.BranchSelector.isBranchSelected(this.props.branch.id);
    }
    get isBranchAllowed() {
        return this.props.branch.id in this.BranchService.allowedBranches;
    }
    get isCurrent() {
        return this.props.branch.id === this.BranchService.currentBranch.id;
    }

    logIntoBranch() {
        if (this.isBranchAllowed) {
            this.BranchSelector.switchBranch("loginto", this.props.branch.id);
        }
    }

    toggleBranch() {
        if (this.isBranchAllowed) {
            this.BranchSelector.switchBranch("toggle", this.props.branch.id);
        }
    }
}
