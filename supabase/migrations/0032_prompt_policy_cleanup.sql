-- =============================================================================
-- NexusWiki 0032: 전역 Ask 템플릿의 낡은 인용 지시 제거
--
-- 관련 이슈: #196, #197
-- 설계 근거: openspec/changes/ai-control-risk-policy/design.md > D1
--
-- 0006의 네 템플릿은 서버 별칭 이전의 `[[wiki:slug]]`, `[[src:청크id]]`를 지시하고, 0012가 그 뒤에
-- 새 별칭 지시를 덧붙여 두 지시가 함께 남았다. 인용 형식은 이제 워커의 공통 정책이 보장한다.
-- 워크스페이스가 만든 템플릿은 건드리지 않는다.
-- 이전 코드와도 호환된다. 0012의 별칭 지시는 그대로 남는다.
-- =============================================================================

begin;

update public.prompt_templates
   set system_prompt = replace(replace(system_prompt,
         '`[[wiki:slug]]`', '위키 별칭'),
         '`[[src:청크id]]`', '원문 별칭')
 where workspace_id is null
   and target_type = 'ask'
   and system_prompt like '%`[[wiki:slug]]`%';

commit;
