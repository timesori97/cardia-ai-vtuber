-- src/lua/endpoints/dismiss.lua
--
-- Added for the Cardia stream (not part of upstream balatrobot).
--
-- Unlocking a deck pops an overlay with a Continue button on top of whatever
-- screen you are on, and the game pauses behind it. The bot API drives game
-- functions directly, so it never presses that button: the popup sat on the
-- broadcast and the run stopped progressing. This closes any overlay that is
-- up and unpauses, and does nothing at all when there is none — so it is safe
-- to call on every poll.

---@type Endpoint
return {

  name = "dismiss",

  description = "Close any overlay/notification menu (e.g. a deck unlock) and unpause",

  schema = {},

  -- deliberately no requires_state: an unlock popup can appear on any screen

  ---@param _args table
  ---@param send_response fun(response: Response.Endpoint)
  execute = function(_args, send_response)
    local had_overlay = G and G.OVERLAY_MENU ~= nil

    -- Deliberately does NOT touch G.SETTINGS.paused. The game pauses itself
    -- while dealing a booster pack; forcing it to resume let the bot act on a
    -- half-built G.pack_cards and crashed the game in pack.lua.
    if had_overlay and G.FUNCS and G.FUNCS.exit_overlay_menu then
      G.FUNCS.exit_overlay_menu()
    end

    if not had_overlay then
      local state = BB_GAMESTATE.get_gamestate()
      state.dismissed = false
      send_response(state)
      return
    end

    -- Wait until the overlay is actually gone before answering, so the caller
    -- never acts on a screen that is still blocked.
    G.E_MANAGER:add_event(Event({
      trigger = "condition",
      blocking = false,
      func = function()
        if G.OVERLAY_MENU == nil then
          local state = BB_GAMESTATE.get_gamestate()
          state.dismissed = true
          send_response(state)
          return true
        end
        return false
      end,
    }))
  end,
}
