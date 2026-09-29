-- Execute UMA VEZ no SQL Editor do seu projeto Supabase antes de usar a atualização.
-- Adiciona campos sem excluir pedidos ou fotos existentes.
alter table public.volumes add column if not exists ordem_servico text;
alter table public.volumes add column if not exists nome_cliente text;
alter table public.volumes add column if not exists peso_bruto numeric;
notify pgrst, 'reload schema';
