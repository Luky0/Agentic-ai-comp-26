
# Repository: projects/anl2026
echo -e "${BLUE}Restoring: projects/anl2026${NC}"
if [ -d "projects/anl2026/.git" ]; then
    echo -e "  ${YELLOW}Directory already exists, skipping...${NC}"
else
    # Create parent directory if needed
    mkdir -p "projects"

    # Clone the repository
    if git clone "git@github.com:autoneg/anl2026.git" "projects/anl2026"; then
        echo -e "  ${GREEN}✓${NC} Successfully cloned"

        # Checkout the original branch if not already on it
        cd "projects/anl2026"
        current=$(git rev-parse --abbrev-ref HEAD)
        if [ "$current" != "main" ]; then
            if git checkout "main" 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} Checked out branch: main"
            else
                echo -e "  ${YELLOW}⚠${NC} Could not checkout branch: main"
            fi
        fi
        cd - > /dev/null
    else
        echo -e "  ${RED}✗${NC} Failed to clone"
    fi
fi

# Repository: projects/anl2026
echo -e "${BLUE}Restoring: projects/anl2026${NC}"
if [ -d "projects/anl2026/.git" ]; then
    echo -e "  ${YELLOW}Directory already exists, skipping...${NC}"
else
    # Create parent directory if needed
    mkdir -p "projects"

    # Clone the repository
    if git clone "git@github.com:autoneg/anl2026.git" "projects/anl2026"; then
        echo -e "  ${GREEN}✓${NC} Successfully cloned"

        # Checkout the original branch if not already on it
        cd "projects/anl2026"
        current=$(git rev-parse --abbrev-ref HEAD)
        if [ "$current" != "main" ]; then
            if git checkout "main" 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} Checked out branch: main"
            else
                echo -e "  ${YELLOW}⚠${NC} Could not checkout branch: main"
            fi
        fi
        cd - > /dev/null
    else
        echo -e "  ${RED}✗${NC} Failed to clone"
    fi
fi

# Repository: projects/anl2026
echo -e "${BLUE}Restoring: projects/anl2026${NC}"
if [ -d "projects/anl2026/.git" ]; then
    echo -e "  ${YELLOW}Directory already exists, skipping...${NC}"
else
    # Create parent directory if needed
    mkdir -p "projects"

    # Clone the repository
    if git clone "git@github.com:autoneg/anl2026.git" "projects/anl2026"; then
        echo -e "  ${GREEN}✓${NC} Successfully cloned"

        # Checkout the original branch if not already on it
        cd "projects/anl2026"
        current=$(git rev-parse --abbrev-ref HEAD)
        if [ "$current" != "main" ]; then
            if git checkout "main" 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} Checked out branch: main"
            else
                echo -e "  ${YELLOW}⚠${NC} Could not checkout branch: main"
            fi
        fi
        cd - > /dev/null
    else
        echo -e "  ${RED}✗${NC} Failed to clone"
    fi
fi

# Repository: projects/anl2026
echo -e "${BLUE}Restoring: projects/anl2026${NC}"
if [ -d "projects/anl2026/.git" ]; then
    echo -e "  ${YELLOW}Directory already exists, skipping...${NC}"
else
    # Create parent directory if needed
    mkdir -p "projects"

    # Clone the repository
    if git clone "git@github.com:autoneg/anl2026.git" "projects/anl2026"; then
        echo -e "  ${GREEN}✓${NC} Successfully cloned"

        # Checkout the original branch if not already on it
        cd "projects/anl2026"
        current=$(git rev-parse --abbrev-ref HEAD)
        if [ "$current" != "main" ]; then
            if git checkout "main" 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} Checked out branch: main"
            else
                echo -e "  ${YELLOW}⚠${NC} Could not checkout branch: main"
            fi
        fi
        cd - > /dev/null
    else
        echo -e "  ${RED}✗${NC} Failed to clone"
    fi
fi

# Repository: projects/anl2026
echo -e "${BLUE}Restoring: projects/anl2026${NC}"
if [ -d "projects/anl2026/.git" ]; then
    echo -e "  ${YELLOW}Directory already exists, skipping...${NC}"
else
    # Create parent directory if needed
    mkdir -p "projects"
    
    # Clone the repository
    if git clone "git@github.com:autoneg/anl2026.git" "projects/anl2026"; then
        echo -e "  ${GREEN}✓${NC} Successfully cloned"
        
        # Checkout the original branch if not already on it
        cd "projects/anl2026"
        current=$(git rev-parse --abbrev-ref HEAD)
        if [ "$current" != "main" ]; then
            if git checkout "main" 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} Checked out branch: main"
            else
                echo -e "  ${YELLOW}⚠${NC} Could not checkout branch: main"
            fi
        fi
        cd - > /dev/null
    else
        echo -e "  ${RED}✗${NC} Failed to clone"
    fi
fi

