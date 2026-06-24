import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { BurgerMenu } from "@web/webclient/burger_menu/burger_menu";
import { MobileSwitchBranchMenu } from "@branch/js/mobile_switch_branch_menu";


export class BranchBurgerMenu extends BurgerMenu {
    static components = { 
        ...BurgerMenu.components, 
        MobileSwitchBranchMenu 
    };

    setup() {
        super.setup();
        this.branch = useService("Branch");
    }
}

const systrayItem = {
    Component: BranchBurgerMenu,
};

registry.category("systray").add("burger_menu", systrayItem, { sequence: 0, force: true });
