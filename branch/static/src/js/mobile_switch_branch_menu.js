import { SwitchBranchMenu } from "@branch/js/session";


export class MobileSwitchBranchMenu extends SwitchBranchMenu {
    static template = "web.MobileSwitchBranchMenu";

    setup() {
        super.setup();
        this.state.isOpen = false;
    }

    get show() {
        return !this.hasLotsOfCompanies || this.state.isOpen === true;
    }

    toggleCollapsible() {
        if (this.hasLotsOfCompanies) {
            this.state.isOpen = !this.state.isOpen;
        }
    }
}
