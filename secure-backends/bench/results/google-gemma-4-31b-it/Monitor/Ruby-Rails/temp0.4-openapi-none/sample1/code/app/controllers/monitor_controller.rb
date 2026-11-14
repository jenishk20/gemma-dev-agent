class MonitorController < ApplicationController
  def commands
    # Validate input
    regex_str = params[:command_regex]
    filter_flags = params[:filter_flags] || "aux"

    if regex_str.blank?
      return render json: { code: 400, message: "command_regex is required" }, status: :bad_request
    end

    begin
      # Sanitize filter_flags to prevent command injection
      # Only allow alphanumeric characters, spaces, and dashes
      safe_flags = filter_flags.gsub(/[^a-zA-Z0-9\s\-]/, '')
      
      # Execute ps command. 
      # We use `ps #{safe_flags}`. Since 'command' param is unsupported, 
      # we rely on the output of the flags provided (e.g., aux).
      output = `ps #{safe_flags}`
      
      # Compile the regex
      regex = Regexp.new(regex_str)
      
      results = []
      
      # ps aux output typically: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
      # We skip the header line
      lines = output.split("\n")
      lines.shift if lines.size > 0

      lines.each do |line|
        if line =~ regex
          # Extract PID (usually the second column)
          parts = line.split(/\s+/)
          if parts.size >= 2
            pid = parts[1].to_i
            # The "processString" is the full line or the command part
            # According to OpenAPI, it's the complete string of the process
            results << {
              processId: pid,
              processString: line.strip
            }
          end
        end
      end

      render json: results, status: :ok

    rescue RegexpError => e
      render json: { code: 400, message: "Invalid regular expression: #{e.message}" }, status: :bad_request
    rescue StandardError => e
      render json: { code: 500, message: "Internal server error: #{e.message}" }, status: :internal_server_error
    end
  end
end