import { ExternalServiceClientImpl, type ExternalServiceClientOptions } from './client.js';

export type ServiceKind = 'user' | 'server';

type CommonMethod = 'checkPermission' | 'getProfile';
type UserOnlyMethod =
  | 'exchangeCode'
  | 'refreshToken'
  | 'getPosts'
  | 'getWarns'
  | 'refreshPosts'
  | 'refreshConnections';
type ServerOnlyMethod =
  | 'listModerators'
  | 'getModeratorConnections'
  | 'refreshModeratorConnections'
  | 'refreshModeratorPosts'
  | 'notifyServer'
  | 'notifyModerator'
  | 'setWebhook'
  | 'deleteWebhook';

export type ExternalServiceClient<K extends ServiceKind = ServiceKind> = Pick<
  ExternalServiceClientImpl,
  | CommonMethod
  | ([K] extends ['user'] ? UserOnlyMethod : never)
  | ([K] extends ['server'] ? ServerOnlyMethod : never)
>;

export const ExternalServiceClient = ExternalServiceClientImpl as {
  new <K extends ServiceKind = ServiceKind>(
    options: ExternalServiceClientOptions,
  ): ExternalServiceClient<K>;
};
