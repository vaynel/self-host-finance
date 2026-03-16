import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Wallet, Mail, Lock, Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";

export default function Login() {
  const navigate = useNavigate();
  const { login, register } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      if (isSignUp) {
        if (!name.trim()) {
          toast.error("이름을 입력해주세요");
          setIsLoading(false);
          return;
        }
        await register(email, password, name);
        toast.success("회원가입이 완료되었습니다");
      } else {
        await login(email, password);
        toast.success("로그인되었습니다");
      }
      navigate("/");
    } catch (error: any) {
      toast.error(error.message || "오류가 발생했습니다");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md space-y-8">
        <div className="flex flex-col items-center gap-3">
          <div className="h-14 w-14 rounded-2xl bg-primary flex items-center justify-center shadow-lg">
            <Wallet className="h-7 w-7 text-primary-foreground" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-bold text-foreground tracking-tight">FinFlow</h1>
            <p className="text-sm text-muted-foreground mt-1">개인 재무 관리 플랫폼</p>
          </div>
        </div>

        <Card className="border-border/50 shadow-xl">
          <CardContent className="pt-6 pb-8 px-8">
            <h2 className="text-lg font-semibold text-foreground mb-6 text-center">
              {isSignUp ? "회원가입" : "로그인"}
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              {isSignUp && (
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-foreground">이름</label>
                  <Input 
                    placeholder="홍길동" 
                    className="h-11"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">이메일</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="email"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="h-11 pl-10"
                    required
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">비밀번호</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="h-11 pl-10 pr-10"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {!isSignUp && (
                <div className="flex justify-end">
                  <button type="button" className="text-xs text-primary hover:underline">
                    비밀번호를 잊으셨나요?
                  </button>
                </div>
              )}

              <Button 
                type="submit" 
                className="w-full h-11 text-sm font-semibold mt-2"
                disabled={isLoading}
              >
                {isLoading ? "처리 중..." : isSignUp ? "가입하기" : "로그인"}
              </Button>
            </form>

            <div className="mt-6 text-center">
              <span className="text-sm text-muted-foreground">
                {isSignUp ? "이미 계정이 있으신가요?" : "계정이 없으신가요?"}{" "}
                <button
                  onClick={() => setIsSignUp(!isSignUp)}
                  className="text-primary font-medium hover:underline"
                >
                  {isSignUp ? "로그인" : "회원가입"}
                </button>
              </span>
            </div>
          </CardContent>
        </Card>

        <p className="text-xs text-muted-foreground text-center">
          © 2026 FinFlow. All rights reserved.
        </p>
      </div>
    </div>
  );
}
