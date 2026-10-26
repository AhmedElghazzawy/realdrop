import { Drawer } from "./Drawer";
import { MenuIcon } from "./icons";

export function MobileMenu({
  labels,
  children,
}: {
  labels: { open: string; close: string };
  children: React.ReactNode;
}) {
  return (
    <Drawer
      trigger={<MenuIcon />}
      triggerClassName="grid size-10 place-items-center lg:hidden"
      label={labels.open}
      closeLabel={labels.close}
    >
      {children}
    </Drawer>
  );
}
