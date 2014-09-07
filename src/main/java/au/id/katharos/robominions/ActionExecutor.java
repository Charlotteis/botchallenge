package au.id.katharos.robominions;

import java.util.HashMap;
import java.util.UUID;
import java.util.logging.Logger;

import org.bukkit.Bukkit;
import org.bukkit.entity.Player;

import au.id.katharos.robominions.ActionQueue.ActionEvent;
import au.id.katharos.robominions.api.RobotApi.RobotActionRequest;

public class ActionExecutor implements Runnable {

	private final ActionQueue actionQueue;
	private final HashMap<UUID, AbstractRobot> robotMap;
	private final HashMap<String, UUID> uuidCache;
	private final Logger logger;
	
	public ActionExecutor(
			ActionQueue actionQueue,
			HashMap<UUID, AbstractRobot> chickenMap,
			HashMap<String, UUID> uuidCache,
			Logger logger) {
		this.actionQueue = actionQueue;
		this.robotMap = chickenMap;
		this.logger = logger;
		this.uuidCache = uuidCache;
	}

	private AbstractRobot getRobot(String playerName) {
		Player player = Bukkit.getPlayer(playerName);
		UUID uuid = uuidCache.get(playerName);
		if (player != null) {
			uuid = player.getUniqueId();
			uuidCache.put(playerName, uuid);
		}
		if (robotMap.containsKey(uuid)) {
			return robotMap.get(uuid);
		}
		return null;
	}
	
	@Override
	public void run() {
		ActionEvent event = actionQueue.getNextEvent();
		while (event != null) {
			
			AbstractRobot robot = getRobot(event.getPlayerId());
			RobotActionRequest actionRequest = event.getActionRequest();
			if (robot != null) {
				// Move chicken according to instruction.
				boolean success = false;
				if (actionRequest.hasMoveDirection()) {
					success = robot.move(actionRequest.getMoveDirection());
				} else if (actionRequest.hasTurnDirection()) {
					success = robot.turn(actionRequest.getTurnDirection());
				} else if (actionRequest.hasMineDirection()) {
					success = robot.mine(actionRequest.getMineDirection());
				} else if (actionRequest.hasPlaceDirection() && actionRequest.hasPlaceMaterial()) {
					success = robot.place(actionRequest.getPlaceDirection(),
							Util.toBukkitMaterial(actionRequest.getPlaceMaterial()));
				}
				event.getListener().call(new ActionQueue.ActionResult(event.getKey(), success));
			} else {
				logger.info("Attempted to move nonexistant chicken for " + event.getPlayerId());
			}
			// Get next event from queue (null if there is none);
			event = actionQueue.getNextEvent();
		}
	}
}
