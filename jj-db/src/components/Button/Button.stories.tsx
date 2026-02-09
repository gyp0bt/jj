import type { Meta, StoryObj } from "@storybook/react";
import { Button } from ".";

const meta: Meta<typeof Button> = {
  title: "Components/Button",
  component: Button,
  parameters: {
    layout: "centered",
  },
  tags: ["autodocs"],
  argTypes: {
    variant: {
      control: "select",
      options: ["primary", "secondary", "ghost"],
    },
    size: {
      control: "select",
      options: ["sm", "md", "lg"],
    },
    disabled: {
      control: "boolean",
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {
  args: {
    variant: "primary",
    children: "保存",
  },
};

export const Secondary: Story = {
  args: {
    variant: "secondary",
    children: "キャンセル",
  },
};

export const Ghost: Story = {
  args: {
    variant: "ghost",
    children: "戻る",
  },
};

export const Small: Story = {
  args: {
    size: "sm",
    children: "小さいボタン",
  },
};

export const Large: Story = {
  args: {
    size: "lg",
    variant: "primary",
    children: "大きいボタン",
  },
};

export const Disabled: Story = {
  args: {
    variant: "primary",
    children: "無効なボタン",
    disabled: true,
  },
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Button variant="primary">Primary</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="ghost">Ghost</Button>
      </div>
      <div className="flex items-center gap-2">
        <Button size="sm">Small</Button>
        <Button size="md">Medium</Button>
        <Button size="lg">Large</Button>
      </div>
    </div>
  ),
};
