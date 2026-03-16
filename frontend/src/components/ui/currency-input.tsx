import * as React from "react";
import { Input } from "./input";
import { cn } from "@/lib/utils";

export interface CurrencyInputProps extends Omit<React.ComponentProps<"input">, "value" | "onChange"> {
  value: string;
  onChange: (value: string) => void;
  prefix?: string;
}

const CurrencyInput = React.forwardRef<HTMLInputElement, CurrencyInputProps>(
  ({ className, value, onChange, prefix = "₩", ...props }, ref) => {
    // 숫자만 추출 (콤마 제거)
    const numericValue = value.replace(/,/g, "");

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const inputValue = e.target.value;
      // 콤마 제거 후 숫자만 추출
      const withoutCommas = inputValue.replace(/,/g, "");
      // 숫자만 허용 (소수점 제외, 정수만)
      const numericOnly = withoutCommas.replace(/[^\d]/g, "");

      // 숫자가 있으면 천 단위 구분자 추가하여 저장
      if (numericOnly) {
        const num = parseInt(numericOnly, 10);
        if (!isNaN(num)) {
          onChange(num.toLocaleString("ko-KR"));
        } else {
          onChange(numericOnly);
        }
      } else {
        onChange("");
      }
    };

    // 표시용 값 (이미 천 단위 구분자가 포함되어 있음)
    const displayValue = value || "";

    return (
      <div className="relative">
        {prefix && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">
            {prefix}
          </span>
        )}
        <Input
          ref={ref}
          type="text"
          inputMode="numeric"
          value={displayValue}
          onChange={handleChange}
          className={cn(prefix && "pl-8", className)}
          {...props}
        />
      </div>
    );
  }
);

CurrencyInput.displayName = "CurrencyInput";

export { CurrencyInput };
