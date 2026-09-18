## 5. End-to-End Execution Example

A walkthrough of a complete execution instance simulated in the jBPM console:

### Stage 1: The Farmstead

<div align="center">
  <img src="images/image6.png" alt="Start" width="80%" />
  <p><em>Starting the quest</em></p>
  <img src="images/image7.png" alt="[Process vars]"  />
    <p><em>Quest process variables and overview</em></p>
  <img src="images/image8.png" alt="[Macro overview]"  />

  <img src="images/image9.png" alt="Search around, set off traps" width="85%" />
  <p><em>Navigating traps: selecting how Geralt handles the farmstead defenses (Geralt carelessly triggers the traps (the last option), which will induce irritation in Letho during their confrontation).</em></p>
  <img src="images/image10.png" alt="Investigate barn" width="75%"/>
  <img src="images/image11.png" alt="Find letho (dialogue)" />
  <p><em>Confronting Letho in the barn; dialogue is conditioned by the 'triggeredTraps' variable.</em></p>
  <img src="images/image12.png" alt="Fight headhunters" width="85%" />
    <p><em>Combat at the farmstead: Geralt chooses to help Letho and must follow him within 30 seconds.</em></p>
  <img src="images/image13.png" alt="Help Letho decision" />
  <img src="images/image14.png" alt="[Parallel tasks: (a) moving with letho and (b)looting corpses (timed)]" />
  <img src="images/image15.png" alt="(a) Move with Letho" width="65%" />
  <img src="images/image16.png" alt="(OR branching)" width="50%" />
  <p><em>Concurrent OR-branch: looting corpses while following Letho.</em></p>
    <img src="images/image17.png" alt="(b) Looting corpses in parallel"  width="90%"/>
</div>



### Stage 2: Finding Louis

<div align="center">
  <img src="images/image18.png" alt="[Macro overview]"  />
  <img src="images/image19.png" alt="Follow Letho to Camp" />
  <p><em>Tracking Louis to his encampment and encountering bandits.</em></p>

  <img src="images/image20.png" alt="Encounter Louis (dialogue)" />
  <img src="images/image21.png" alt="Fight bandits" width="65%" />
  <p><em>Battle outcome: a lost fight loops back to the start of the subquest via XOR-join.</em></p>

  <img src="images/image22.png" alt="Defeat restart loop" width="56%" />
  <img src="images/image23.png" alt="(anew) Follow Letho to Camp" />
  <img src="images/image24.png" alt="Encounter Louis (dialogue)"  />
  <img src="images/image25.png" alt="Fight bandits" width="65%" />
  <img src="images/image26.png" alt="[Parallel split]" />

  <img src="images/image27.png" alt="loot corpses" width="75%" />
  <img src="images/image29.png" alt="Kill Louis?" width="65%" />
</div>


### Stage 3: Dealing with Bounty Hunters 

<div align="center">
  <img src="images/image30.png" alt="[Macro overview]" />

  <img src="images/image31.png" alt="Head to Livendale and find Bounty Hunters" />
  <img src="images/image32.png" alt="Cutscene: Letho confronts Bounty Hunters" width="90%" />
  <img src="images/image33.png" alt="Intervene?" width="75%" />
  <p><em>Confronting bounty hunters: Geralt decides whether to draw his sword or negotiate.</em></p>
  <img src="images/image34.png" alt="Fight and kill bandits" width="80%"/>
  <img src="images/image35.png" alt="Final dialogue branch. Letho survives (dialogue). Invite him to Kaer Morhen?" />
    <p><em>If Geralt invites Letho to Kaer Morhen.</em></p>
  <img src="images/image36.png" alt="Go to Kaer Morhen" width="90%" />
  <p><em>Quest completion: total reward and inventory updated in process variables.</em></p>
    <img src="images/image37.png" alt="[Macro overview: Completed process instance]" width="80%" />
</div>

### Execution Path & Process Assets

<div align="center">

  <img src="images/image38.png" alt="Final state" width="80%" />
  <img src="images/image39.png" alt="Macro overview: active tokens trace"/>
  <p><em>Figure 6: Final token execution trace highlighting the path traversed through the model.</em></p>
</div>
