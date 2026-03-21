import {
  LayoutDashboard,
  ArrowLeftRight,
  Landmark,
  TrendingUp,
  BarChart3,
  Upload,
  Settings,
  SlidersHorizontal,
  Wallet,
  LogOut,
  User,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import { NavLink } from "@/components/NavLink";
import { useLocation } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
  useSidebar,
} from "@/components/ui/sidebar";

const mainItems = [
  { title: "대시보드", url: "/", icon: LayoutDashboard },
  { title: "거래 내역", url: "/transactions", icon: ArrowLeftRight },
  { title: "계좌 관리", url: "/accounts", icon: Landmark },
  { title: "투자 관리", url: "/investments", icon: TrendingUp },
  { title: "리포트", url: "/reports", icon: BarChart3 },
];

const toolItems = [
  { title: "데이터 업로드", url: "/upload", icon: Upload },
  { title: "설정", url: "/settings", icon: Settings },
  { title: "설정 관리", url: "/settings/mgmt", icon: SlidersHorizontal },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const location = useLocation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="p-4">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center flex-shrink-0">
            <Wallet className="h-4 w-4 text-primary-foreground" />
          </div>
          {!collapsed && (
            <div>
              <h1 className="text-sm font-bold text-sidebar-primary-foreground tracking-tight">FinFlow</h1>
              <p className="text-[10px] text-sidebar-foreground/60">개인 재무 관리</p>
            </div>
          )}
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>메인</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {mainItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild tooltip={item.title}>
                    <NavLink
                      to={item.url}
                      end={item.url === "/"}
                      className="hover:bg-sidebar-accent/50"
                      activeClassName="bg-sidebar-accent text-sidebar-primary font-medium"
                    >
                      <item.icon className="h-4 w-4" />
                      {!collapsed && <span>{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>도구</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {toolItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild tooltip={item.title}>
                    <NavLink
                      to={item.url}
                      className="hover:bg-sidebar-accent/50"
                      activeClassName="bg-sidebar-accent text-sidebar-primary font-medium"
                    >
                      <item.icon className="h-4 w-4" />
                      {!collapsed && <span>{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-3 space-y-2">
        {user && !collapsed && (
          <div className="flex items-center gap-3 rounded-lg bg-sidebar-accent/50 p-3">
            <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
              <User className="h-4 w-4 text-sidebar-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-sidebar-foreground truncate">{user.name}</p>
              <p className="text-[10px] text-sidebar-foreground/60 truncate">{user.email}</p>
            </div>
            <button onClick={handleLogout} className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        )}
        {user && collapsed && (
          <button onClick={handleLogout} className="w-full flex justify-center p-2 text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">
            <LogOut className="h-4 w-4" />
          </button>
        )}
        {!collapsed && (
          <div className="rounded-lg bg-sidebar-accent/50 p-3">
            <p className="text-[10px] text-sidebar-foreground/60">마지막 동기화</p>
            <p className="text-xs text-sidebar-foreground font-mono">2026.03.11 09:30</p>
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
