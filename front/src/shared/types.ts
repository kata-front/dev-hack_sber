export type startAction = 'join' | 'create' | null

export type LoginResponse = {
    ok: boolean;
    roomId?: number;
}