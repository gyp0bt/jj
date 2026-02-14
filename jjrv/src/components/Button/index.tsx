import type { ComponentProps } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends ComponentProps<"button"> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-neutral-900 text-white border-transparent hover:bg-neutral-800 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-100",
  secondary:
    "bg-white text-neutral-900 border-neutral-200 hover:bg-neutral-50 dark:bg-neutral-900 dark:text-white dark:border-neutral-700 dark:hover:bg-neutral-800",
  ghost:
    "bg-transparent text-neutral-700 border-transparent hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-2.5 py-1.5 text-sm",
  md: "px-3 py-2 text-sm",
  lg: "px-4 py-2.5 text-base",
};

export function Button({
  variant = "secondary",
  size = "md",
  className = "",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`
        inline-flex items-center justify-center gap-2
        rounded-xl border font-medium
        transition-colors duration-150
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${className}
      `
        .trim()
        .replace(/\s+/g, " ")}
      {...props}
    >
      {children}
    </button>
  );
}
