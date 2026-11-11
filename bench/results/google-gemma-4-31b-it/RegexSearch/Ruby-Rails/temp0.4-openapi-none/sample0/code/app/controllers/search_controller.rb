class SearchController < ApplicationController
  def index
    regex_param = params[:regex]
    directory_param = params[:directory] || ""
    recursive_param = params[:recursive] == 'true'

    if regex_param.blank?
      return render json: { error: "regex parameter is required" }, status: :bad_request
    end

    begin
      regex = Regexp.new(regex_param)
    rescue RegexpError => e
      return render json: { error: "Invalid regex pattern: #{e.message}" }, status: :bad_request
    end

    # Define the root directory for files
    root_path = Rails.root.join('files')
    
    # Resolve the target search directory
    # We use File.expand_path and check if it starts with root_path to prevent directory traversal attacks
    target_dir = File.expand_path(File.join(root_path, directory_param), root_path)

    unless target_dir.start_with?(root_path.to_s) && Dir.exist?(target_dir)
      return render json: { error: "Invalid or inaccessible directory" }, status: :bad_request
    end

    matching_files = []
    
    begin
      # Determine glob pattern based on recursive flag
      pattern = recursive_param ? File.join(target_dir, "**", "*") : File.join(target_dir, "*")
      
      Dir.glob(pattern).each do |path|
        next if File.directory?(path)

        begin
          content = File.read(path)
          if content =~ regex
            # Calculate path relative to the requested directory_param
            relative_path = path.sub(/^#{Regexp.escape(target_dir)}\/?/, '')
            matching_files << relative_path
          end
        rescue StandardError => e
          # Skip files that cannot be read (permissions, etc)
          next
        end
      end
    rescue StandardError => e
      return render json: { error: "Internal server error during search: #{e.message}" }, status: :internal_server_error
    end

    render json: { files: matching_files }, status: :ok
  end
end