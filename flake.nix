{
  description = "Dygma Defy MIDI bridge dev shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };

      python = pkgs.python3.withPackages (ps: with ps; [
        evdev
        python-rtmidi
      ]);
    in
    {
      apps.${system}.default = {
        type = "app";
        program = "${pkgs.writeShellScript "defy-midi" ''
          exec ${python}/bin/python ${self}/defy-midi.py
        ''}";
      };

      devShells.${system}.default = pkgs.mkShell {
        packages = [
          python
          pkgs.uv
          pkgs.evtest
          pkgs.alsa-utils
        ];

        shellHook = ''
          export DEFY_KBD="/dev/input/by-id/usb-DYGMA_DEFY_235779CEB34CC05D-if02-event-kbd"

          echo "Defy MIDI dev shell"
          echo
          echo "Commands:"
          echo "  defy-evtest     Run evtest on the Defy keyboard device"
          echo "  defy-midi       Run ./defy-midi.py"
          echo "  defy-connect    Connect Defy MIDI to Midi Through"
          echo "  defy-status     Show ALSA MIDI ports"
          echo

          defy-evtest() {
            sudo "$(command -v evtest)" "$DEFY_KBD"
          }

          defy-midi() {
            python ./defy-midi.py
          }

          defy-status() {
            aconnect -l
          }

          defy-connect() {
            local src
            src="$(aconnect -l | awk '
              /RtMidiOut Client/ { client=$2; gsub(":", "", client) }
              /Defy MIDI/ && client != "" { print client ":0"; exit }
            ')"

            if [ -z "$src" ]; then
              echo "Could not find Defy MIDI / RtMidiOut Client. Is defy-midi running?"
              return 1
            fi

            echo "Connecting $src -> 14:0 (Midi Through)"
            aconnect "$src" 14:0
          }

          defy-start() {
            defy-midi
          }
        '';
      };
    };
}
