import { notifications } from "@mantine/notifications";

export const notify = {
  error: (message: string, title = "Something went wrong") =>
    notifications.show({ color: "red", title, message }),
  success: (message: string, title?: string) =>
    notifications.show({ color: "teal", title, message }),
  info: (message: string, title?: string) =>
    notifications.show({ color: "blue", title, message }),
};
