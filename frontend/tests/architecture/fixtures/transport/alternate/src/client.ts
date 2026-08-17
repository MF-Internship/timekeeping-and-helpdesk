import axios from "axios";

export const unsafe = () => axios.get("/api/v1/probe/");
