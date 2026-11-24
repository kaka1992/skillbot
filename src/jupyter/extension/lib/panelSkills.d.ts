export declare function enterSkillsMode(panel: any): void;
export declare function exitSkillsMode(panel: any): void;
export declare function renderSkillList(panel: any, skills: Array<{
    name: string;
    description: string;
    enabled: boolean;
    body?: string;
}>): void;
export declare function onSkillKeydown(panel: any, e: KeyboardEvent): void;
export declare function refreshSkillRows(panel: any): void;
export declare function renderSkillInfo(panel: any, skill: {
    name: string;
    description: string;
    enabled: boolean;
    body: string;
    path: string;
}): void;
