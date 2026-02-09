export const colorClasses = (color: string) => {
  switch (color) {
    case "sky":
      return {
        border: "border-gray-300 dark:border-gray-600",
        bg: "bg-sky-50/70 dark:bg-sky-800/50",
        text: "text-sky-900 dark:text-sky-100",
        left: "border-l-4 border-sky-400",
      };
    case "teal":
      return {
        border: "border-gray-300 dark:border-gray-600",
        bg: "bg-teal-50/70 dark:bg-teal-800/50",
        text: "text-teal-900 dark:text-teal-100",
        left: "border-l-4 border-teal-400",
      };
    case "slate":
      return {
        border: "border-gray-300 dark:border-gray-600",
        bg: "bg-slate-50/70 dark:bg-slate-800/50",
        text: "text-slate-900 dark:text-slate-100",
        left: "border-l-4 border-slate-400",
      };
    case "violet":
      return {
        border: "border-gray-300 dark:border-gray-600",
        bg: "bg-violet-50/70 dark:bg-violet-800/50",
        text: "text-violet-900 dark:text-violet-100",
        left: "border-l-4 border-violet-400",
      };
    default:
      return {
        border: "border-gray-300 dark:border-gray-600",
        bg: "bg-neutral-50/70 dark:bg-neutral-800/50",
        text: "text-neutral-900 dark:text-neutral-100",
        left: "border-l-4 border-neutral-400",
      };
  }
};

export const chip =
  "inline-flex items-center rounded-full px-2 py-0.5 text-[12px]";
