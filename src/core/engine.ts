import { Logger } from "./logger";
import { APP_NAME } from "./constants";

export class ASHEngine {
  static start() {
    Logger.info(`${APP_NAME} Started`);
  }

  static stop() {
    Logger.info(`${APP_NAME} Stopped`);
  }
}