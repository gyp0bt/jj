"use client";
import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/Button";

export interface BackButtonProps {
  label?: string;
  href?: string;
}

export function BackButton({ label = "戻る", href }: BackButtonProps) {
  const router = useRouter();

  const handleClick = () => {
    if (href) {
      router.push(href);
    } else {
      router.back();
    }
  };

  return (
    <Button variant="secondary" onClick={handleClick}>
      <ArrowLeft size={18} />
      {label}
    </Button>
  );
}
