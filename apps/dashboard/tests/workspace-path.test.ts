import { describe, expect, it } from 'vitest';

import { workspacePath } from '@/lib/workspace-path';

describe('workspacePath', () => {
  it('워크스페이스 경로를 만들고 빈 식별자를 거부한다', () => {
    expect(workspacePath('abc')).toBe('/w/abc');
    expect(() => workspacePath('')).toThrow(TypeError);
    expect(() => workspacePath('   ')).toThrow(TypeError);
  });
});
